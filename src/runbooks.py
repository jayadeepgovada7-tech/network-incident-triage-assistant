from src.data_loader import load_runbooks

FALLBACK = {
    "RB-001": (["link_down", "interface_down", "if_down"], ["core", "pe", "ce"]),
    "RB-002": (["device_unreachable", "node_down", "ping_fail"], ["core", "pe", "ce", "switch", "fw"]),
    "RB-003": (["high_latency", "packet_loss", "jitter"], ["core", "pe", "ce", "switch"]),
    "RB-004": (["auth_fail", "authentication_failure", "radius_reject", "8021x_fail"], ["ap", "switch", "fw"]),
    "RB-005": (["bgp_down", "bgp_flap", "neighbor_down", "ospf_neighbor_down"], ["core", "pe", "ce"]),
    "RB-006": (["power_fail", "ups_on_battery", "site_power", "pdu_down"], ["core", "pe", "ce", "switch", "fw", "ap"]),
    "RB-007": (["dns_fail", "resolver_down", "nxdomain_spike"], ["fw", "core", "pe"]),
}

FALLBACK_STEPS = {
    "RB-001": [
        "Confirm interface admin status and last flap time on the local device.",
        "Check far-end device reachability (mgmt VRF ping).",
        "If both ends down, suspect fibre or power, not config.",
        "If one end up, check SFP, light levels, and error counters.",
        "If the device is core or PE, confirm the backup path is forwarding before any bounce.",
    ],
    "RB-002": [
        "Confirm the unreachable alert is still active (not a one-probe blip).",
        "Ping from a second source, not only the NMS.",
        "Check the upstream neighbor: is the interface toward this device down?",
        "If the upstream link is down, treat this as a path failure — do not reboot yet.",
        "If upstream is up and the device is still dark, check site power / console.",
    ],
    "RB-003": [
        "Note the latency value and the interface / destination in the alert.",
        "Check whether an upstream neighbor has link_down or device_unreachable in the same window.",
        "If upstream is down, treat latency as a symptom — do not tune QoS yet.",
        "If upstream is up, check interface errors, drops, and utilisation on the path.",
        "Compare primary vs backup path latency before changing routing.",
    ],
    "RB-004": [
        "Count how many failures and on how many devices.",
        "If it is one AP and a low customer count, treat as local / low priority.",
        "Check whether a AAA / RADIUS server is also alerting.",
        "Do not merge this with a WAN link_down at another site.",
        "If many APs fail at once, check RADIUS reachability.",
    ],
    "RB-005": [
        "Match the BGP neighbor to inventory and to a topology link.",
        "If the underlying interface is already down, this is a symptom of the link — do not debug BGP first.",
        "If the interface is up, check hold timer, prefixes, and recent flaps.",
        "Confirm whether the backup neighbor is still established.",
        "Do not clear BGP on a core or PE until backup forwarding is confirmed.",
    ],
    "RB-006": [
        "Group by site first. Several hostnames at one site is one power event.",
        "If a UPS / PDU alert exists, do not chase each link as a fibre cut.",
        "Confirm other sites are still up.",
        "List customers served at that site only.",
        "Hand off to facilities / on-site if power is confirmed.",
    ],
    "RB-007": [
        "Confirm whether WAN / core links are up. If the path is down, DNS is a symptom.",
        "Check which resolver IP is in the alert.",
        "Try a second resolver before restarting the first.",
        "Do not change routing to fix DNS.",
        "If only one branch reports DNS and WAN is up, check the local CE/firewall DNS setting.",
    ],
}


def parse_list(value):
    return [part.strip().lower() for part in value.replace("|", ",").split(",") if part.strip()]


def extract_steps(text, runbook_id):
    actions = []
    capture = False
    for raw in (text or "").replace("\r", "").splitlines():
        line = raw.strip()
        low = line.lower()
        if low.startswith("## first action"):
            capture = True
            continue
        if capture and line.startswith("##"):
            break
        if capture:
            step = line
            for prefix in ("- ", "* ", "• "):
                if step.startswith(prefix):
                    step = step[len(prefix):].strip()
                    break
            else:
                stripped = step.lstrip("0123456789")
                if stripped != step and stripped[:1] in ".)":
                    step = stripped[1:].strip()
                else:
                    continue
            if step:
                actions.append({"step": step, "source_runbook": runbook_id})
    if actions:
        return actions
    return [
        {"step": s, "source_runbook": runbook_id}
        for s in FALLBACK_STEPS.get(runbook_id, [])
    ]


def parse_runbook(book):
    types = []
    roles = []
    text = (book.get("text") or "").replace("\r", "")
    for raw in text.splitlines():
        line = raw.strip()
        low = line.lower()
        if low.startswith("applies_to_alert_types:") or low.startswith("applies_to:"):
            rhs = line.split(":", 1)[1] if ":" in line else ""
            types.extend(parse_list(rhs.replace("alert_type=", "").replace("roles=", " ")))
        if low.startswith("applies_to_roles:"):
            roles.extend(parse_list(line.split(":", 1)[1]))

    fallback_types, fallback_roles = FALLBACK.get(book["id"], ([], []))
    if not types:
        types = fallback_types
    if not roles:
        roles = fallback_roles

    return {
        "id": book["id"],
        "title": book["title"],
        "filename": book["filename"],
        "alert_types": sorted(set(types)),
        "roles": sorted(set(roles)),
        "text": book["text"],
        "steps": extract_steps(book.get("text"), book["id"]),
    }


def all_runbooks():
    return [parse_runbook(b) for b in load_runbooks()]


def match_runbooks(incident):
    books = all_runbooks()
    alert_types = {t.lower() for t in (incident.get("alert_types") or [])}
    roles = {(a.get("role") or "unknown").lower() for a in incident.get("alerts") or []}

    matches = []
    for book in books:
        matched_types = sorted(alert_types.intersection(book["alert_types"]))
        role_hit = bool(roles.intersection(book["roles"])) if book["roles"] else True
        if matched_types and role_hit:
            matches.append(
                {
                    "id": book["id"],
                    "title": book["title"],
                    "matched_types": matched_types,
                    "why": "alert types " + ", ".join(matched_types),
                    "steps": book["steps"],
                }
            )

    covered = set()
    for match in matches:
        covered.update(match["matched_types"])
    uncovered = sorted(t for t in alert_types if t not in covered)

    guided_steps = []
    seen = set()
    for match in matches:
        for step in match["steps"]:
            key = (step["source_runbook"], step["step"])
            if key not in seen:
                seen.add(key)
                guided_steps.append(step)

    return {
        "matched": matches,
        "uncovered_alert_types": uncovered,
        "guided_steps": guided_steps,
        "escalate_for_runbook": len(uncovered) > 0 or len(matches) == 0,
    }