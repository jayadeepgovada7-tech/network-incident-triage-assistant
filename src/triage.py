from src.correlator import correlate
from src.data_loader import load_devices, load_topology
from src.gemini_client import recommend, fallback_note
from src.runbooks import match_runbooks, all_runbooks


def _resolution(incident):
    matched = incident.get("runbooks") or []
    uncovered = incident.get("uncovered_alert_types") or []
    unknown_devices = incident.get("unknown_devices") or []

    if matched and not uncovered and not unknown_devices:
        return {
            "mode": "guide",
            "matched_runbook_ids": [b["id"] for b in matched],
            "unmatched_types": [],
            "human_summary": "",
        }
    if matched:
        bits = []
        if uncovered:
            bits.append("No runbook for: " + ", ".join(uncovered))
        if unknown_devices:
            bits.append("Device not in inventory: " + ", ".join(unknown_devices))
        return {
            "mode": "split",
            "matched_runbook_ids": [b["id"] for b in matched],
            "unmatched_types": uncovered,
            "human_summary": ". ".join(bits) + ". Leave this part for an engineer.",
        }
    return {
        "mode": "human",
        "matched_runbook_ids": [],
        "unmatched_types": uncovered,
        "human_summary": (
            "No runbook matches "
            + (", ".join(uncovered) if uncovered else "this incident")
            + ". Left for an engineer to solve."
        ),
    }


def attach_runbooks(result):
    books = all_runbooks()
    type_to_books = {}
    for book in books:
        for t in book["alert_types"]:
            type_to_books.setdefault(t, []).append(book)

    for incident in result["incidents"]:
        rb = match_runbooks(incident)
        incident["runbooks"] = rb["matched"]
        incident["uncovered_alert_types"] = rb["uncovered_alert_types"]
        incident["guided_steps"] = rb["guided_steps"]
        incident["escalate_reason"] = []
        incident["resolution"] = _resolution(incident)
        incident["escalate"] = incident["resolution"]["mode"] != "guide"
        if incident["unknown_devices"]:
            incident["escalate_reason"].append(
                "device not in inventory: " + ", ".join(incident["unknown_devices"])
            )
        if incident["resolution"]["mode"] == "human":
            incident["escalate_reason"].append("no runbook matched — left for engineer")
        if incident["resolution"]["unmatched_types"]:
            incident["escalate_reason"].append(
                "uncovered alert types: " + ", ".join(incident["resolution"]["unmatched_types"])
            )

    for item in result["noise"]:
        hits = type_to_books.get((item.get("type") or "").lower(), [])
        if hits:
            item["resolution"] = "guide"
            item["runbooks"] = [{"id": b["id"], "title": b["title"]} for b in hits]
            item["guided_steps"] = hits[0]["steps"]
            item["why_noise"] = (item.get("why_noise") or "low-impact local alert") + " — optional local runbook"
        else:
            item["resolution"] = "human"
            item["runbooks"] = []
            item["guided_steps"] = []
            item["why_noise"] = (item.get("why_noise") or "low-impact local alert") + " — no runbook, left for engineer"
    return result


def triage(alerts):
    devices = load_devices()
    topology = load_topology()
    result = correlate(alerts, devices, topology)
    result = attach_runbooks(result)

    for incident in result["incidents"]:
        if incident["resolution"]["mode"] == "human":
            note = fallback_note(incident)
            note["recommended_actions"] = []
            note["escalate"] = True
            note["escalate_reason"] = incident["resolution"]["human_summary"]
            note["handoff"] = incident["resolution"]["human_summary"]
            incident["note"] = note
        else:
            note = recommend(incident)
            if not note.get("recommended_actions"):
                note["recommended_actions"] = incident.get("guided_steps") or []
            incident["note"] = note
            if note.get("escalate"):
                incident["escalate"] = True
        if not incident.get("guided_steps"):
            incident["guided_steps"] = incident["note"].get("recommended_actions") or []

    result["llm"] = "guide only from matched runbooks; unmatched errors are left for a human"
    return result