from datetime import datetime, timezone
from collections import defaultdict

WINDOW_SECONDS = 15 * 60
DEDUPE_SECONDS = 5 * 60

NOISE_TYPES = {
    "auth_fail",
    "authentication_failure",
    "radius_reject",
    "8021x_fail",
    "cpu_spike",
}

ROLE_WEIGHT = {
    "core": 40,
    "pe": 35,
    "ce": 20,
    "fw": 15,
    "switch": 10,
    "ap": 5,
    "unknown": 5,
}


def parse_ts(ts):
    if not ts:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def seconds_apart(a, b):
    return abs((parse_ts(a["ts"]) - parse_ts(b["ts"])).total_seconds())


def device_map(devices):
    return {d["hostname"]: d for d in devices}


def neighbor_map(topology):
    graph = defaultdict(set)
    for link in topology.get("links", []):
        graph[link["a"]].add(link["b"])
        graph[link["b"]].add(link["a"])
    return graph


def normalize(alerts, devices):
    inv = device_map(devices)
    out = []
    for raw in alerts:
        host = raw.get("device") or "UNKNOWN"
        info = inv.get(host, {})
        out.append(
            {
                "alert_id": raw.get("alert_id"),
                "ts": raw.get("ts"),
                "device": host,
                "site": raw.get("site") or info.get("site") or "UNKNOWN",
                "type": (raw.get("type") or "unknown").lower(),
                "severity": raw.get("severity") or "warning",
                "message": raw.get("message") or "",
                "iface": raw.get("iface"),
                "peer": raw.get("peer"),
                "role": info.get("role", "unknown"),
                "criticality": info.get("criticality", "P4"),
                "customers_served": info.get("customers_served", 0),
                "in_inventory": host in inv,
                "count": 1,
            }
        )
    return out


def dedupe(alerts):
    """Same device + type + iface within 5 minutes → one alert with a count."""
    kept = []
    for alert in sorted(alerts, key=lambda x: x["ts"] or ""):
        merged = False
        for existing in kept:
            same = (
                existing["device"] == alert["device"]
                and existing["type"] == alert["type"]
                and existing["iface"] == alert["iface"]
            )
            if same and seconds_apart(existing, alert) <= DEDUPE_SECONDS:
                existing["count"] += 1
                existing["alert_ids"] = existing.get("alert_ids", [existing["alert_id"]])
                existing["alert_ids"].append(alert["alert_id"])
                merged = True
                break
        if not merged:
            alert["alert_ids"] = [alert["alert_id"]]
            kept.append(alert)
    return kept


class UnionFind:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


def is_noise_type(alert):
    return alert["type"] in NOISE_TYPES


def should_merge(a, b, neighbors):
    if seconds_apart(a, b) > WINDOW_SECONDS:
        return None

    # Noise only joins the same noise on the same device (or same AP site).
    if is_noise_type(a) or is_noise_type(b):
        if a["type"] == b["type"] and a["device"] == b["device"]:
            return "same device + same noise type"
        if a["type"] == b["type"] and a["site"] == b["site"] and a["role"] == "ap":
            return "same site AP auth noise"
        return None

    if a["device"] == b["device"]:
        return "same device"

    if b["device"] in neighbors.get(a["device"], set()):
        return "topology neighbors"

    if a.get("peer") == b["device"] or b.get("peer") == a["device"]:
        return "alert peer matches device"

    return None


def impact_score(members):
    score = 0
    roles = {m["role"] for m in members}
    customers = max((m["customers_served"] for m in members), default=0)
    score += max((ROLE_WEIGHT.get(m["role"], 5) for m in members), default=5)
    score += min(customers / 100, 80)
    if "core" in roles:
        score += 20
    if "core" in roles and "pe" in roles:
        score += 30
    types = {m["type"] for m in members}
    if "link_down" in types and "device_unreachable" in types:
        score += 15
    return round(score, 1)


def priority_from_score(score):
    if score >= 80:
        return "P1"
    if score >= 50:
        return "P2"
    if score >= 20:
        return "P3"
    return "P4"


def incident_title(members):
    types = sorted({m["type"] for m in members})
    devices = sorted({m["device"] for m in members})
    sites = sorted({m["site"] for m in members})
    return f"{', '.join(types)} on {', '.join(devices)} ({', '.join(sites)})"


def correlate(raw_alerts, devices, topology):
    if not raw_alerts:
        return {"incidents": [], "noise": [], "stats": {"input": 0, "after_dedupe": 0}}

    normalized = normalize(raw_alerts, devices)
    deduped = dedupe(normalized)
    neighbors = neighbor_map(topology)

    n = len(deduped)
    uf = UnionFind(n)
    reasons = defaultdict(list)

    for i in range(n):
        for j in range(i + 1, n):
            reason = should_merge(deduped[i], deduped[j], neighbors)
            if reason:
                uf.union(i, j)
                reasons[(i, j)].append(reason)

    clusters = defaultdict(list)
    for i, alert in enumerate(deduped):
        clusters[uf.find(i)].append(i)

    incidents = []
    noise = []

    for root, indexes in clusters.items():
        members = [deduped[i] for i in indexes]
        cluster_reasons = []
        for i in indexes:
            for j in indexes:
                if i < j:
                    cluster_reasons.extend(reasons.get((i, j), []))
        cluster_reasons = sorted(set(cluster_reasons))

        # A single leftover noise alert is noise, not an incident.
        if len(members) == 1 and is_noise_type(members[0]):
            item = dict(members[0])
            item["why_noise"] = "low-impact local alert, not joined to any network incident"
            noise.append(item)
            continue

        score = impact_score(members)
        incidents.append(
            {
                "id": f"INC-{len(incidents) + 1:03d}",
                "title": incident_title(members),
                "priority": priority_from_score(score),
                "impact_score": score,
                "why_grouped": cluster_reasons or ["single alert"],
                "devices": sorted({m["device"] for m in members}),
                "sites": sorted({m["site"] for m in members}),
                "alert_types": sorted({m["type"] for m in members}),
                "unknown_devices": [
                    m["device"] for m in members if not m["in_inventory"]
                ],
                "alerts": members,
            }
        )

    incidents.sort(key=lambda x: x["impact_score"], reverse=True)
    return {
        "incidents": incidents,
        "noise": noise,
        "stats": {
            "input": len(raw_alerts),
            "after_dedupe": len(deduped),
            "incidents": len(incidents),
            "noise": len(noise),
        },
    }