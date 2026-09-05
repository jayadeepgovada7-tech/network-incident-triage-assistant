from datetime import datetime, timezone
from threading import Lock

_lock = Lock()
_alerts = []
_version = 0


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _as_list(payload):
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if isinstance(payload.get("alerts"), list):
            return payload["alerts"]
        return [payload]
    return []


def _normalize_one(item, index):
    if not isinstance(item, dict):
        return None
    labels = item.get("labels") if isinstance(item.get("labels"), dict) else {}
    notes = item.get("annotations") if isinstance(item.get("annotations"), dict) else {}
    device = (
        item.get("device")
        or item.get("host")
        or item.get("hostname")
        or labels.get("device")
        or labels.get("host")
        or labels.get("instance")
        or "UNKNOWN"
    )
    alert_type = (
        item.get("type")
        or item.get("alertname")
        or labels.get("alertname")
        or labels.get("type")
        or "unknown"
    )
    severity = (
        item.get("severity")
        or labels.get("severity")
        or item.get("status")
        or "warning"
    )
    message = (
        item.get("message")
        or notes.get("summary")
        or notes.get("description")
        or item.get("summary")
        or str(alert_type)
    )
    ts = item.get("ts") or item.get("startsAt") or item.get("time") or _now()
    if isinstance(ts, str) and ts.endswith("+00:00"):
        ts = ts.replace("+00:00", "Z")
    iface = item.get("iface") or item.get("interface") or labels.get("interface")
    peer = item.get("peer") or labels.get("peer")
    site = item.get("site") or labels.get("site")
    return {
        "alert_id": item.get("alert_id") or f"MON-{_version + index + 1:04d}",
        "ts": ts,
        "device": str(device),
        "site": site,
        "type": str(alert_type).lower().replace(" ", "_"),
        "severity": str(severity).lower(),
        "message": str(message),
        "iface": iface,
        "peer": peer,
        "source": "monitor",
    }


def ingest(payload):
    global _version
    incoming = []
    for i, raw in enumerate(_as_list(payload)):
        item = _normalize_one(raw, i)
        if item:
            incoming.append(item)
    with _lock:
        _alerts.extend(incoming)
        _version += 1
        snapshot_alerts = list(_alerts)
        version = _version
    return {
        "added": len(incoming),
        "count": len(snapshot_alerts),
        "version": version,
        "alerts": snapshot_alerts,
    }


def snapshot():
    with _lock:
        return {"count": len(_alerts), "version": _version, "alerts": list(_alerts)}


def clear():
    global _version
    with _lock:
        _alerts.clear()
        _version += 1
        return {"count": 0, "version": _version, "alerts": []}