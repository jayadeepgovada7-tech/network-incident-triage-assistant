import json
import re

from src.config import GEMINI_API_KEY, GEMINI_MODEL
from src.data_loader import load_runbooks

_working_model = None


def _strip_json(text):
    if not text:
        return None
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None


def fallback_note(incident):
    actions = list(incident.get("guided_steps") or [])
    if not actions:
        books = {b["id"]: b for b in load_runbooks()}
        for match in incident.get("runbooks") or []:
            text = books.get(match["id"], {}).get("text", "")
            capture = False
            for line in text.splitlines():
                if line.strip().lower().startswith("## first action"):
                    capture = True
                    continue
                if capture and line.startswith("## "):
                    break
                if capture and line.strip()[:1].isdigit():
                    actions.append(
                        {
                            "step": line.strip().lstrip("0123456789.").strip(),
                            "source_runbook": match["id"],
                        }
                    )
    escalate = bool(incident.get("escalate"))
    reasons = incident.get("escalate_reason") or []
    human = (incident.get("resolution") or {}).get("human_summary") or ""
    return {
        "summary": incident.get("title"),
        "priority": incident.get("priority"),
        "recommended_actions": actions[:8],
        "what_was_grouped": incident.get("why_grouped") or [],
        "unknowns": incident.get("uncovered_alert_types") or [],
        "escalate": escalate,
        "escalate_reason": "; ".join(reasons) or human,
        "handoff": human or "Follow the cited runbook steps. Do not invent extra fixes.",
        "llm_used": False,
    }


def _prompt(incident):
    allowed_ids = [b["id"] for b in incident.get("runbooks") or []]
    books = {b["id"]: b["text"] for b in load_runbooks()}
    runbook_text = "\n\n".join(books[i] for i in allowed_ids if i in books) or "NONE"
    compact = {
        "id": incident.get("id"),
        "title": incident.get("title"),
        "priority": incident.get("priority"),
        "why_grouped": incident.get("why_grouped"),
        "devices": incident.get("devices"),
        "sites": incident.get("sites"),
        "alert_types": incident.get("alert_types"),
        "uncovered_alert_types": incident.get("uncovered_alert_types"),
        "guided_steps": incident.get("guided_steps"),
        "resolution": incident.get("resolution"),
        "alerts": [
            {
                "alert_id": a.get("alert_id"),
                "device": a.get("device"),
                "type": a.get("type"),
                "message": a.get("message"),
                "count": a.get("count"),
            }
            for a in incident.get("alerts") or []
        ],
        "allowed_runbook_ids": allowed_ids,
    }
    return f"""You are a NOC triage assistant.
If a runbook matches, write a short ordered action list using ONLY those runbooks.
If an alert type has no runbook, do not invent a fix. Leave it for a human.
Every action MUST cite a runbook id from allowed_runbook_ids.

INCIDENT JSON:
{json.dumps(compact, indent=2)}

RUNBOOKS:
{runbook_text}

Return JSON only with keys:
summary, priority, recommended_actions (list of {{step, source_runbook}}),
what_was_grouped, unknowns, escalate, escalate_reason, handoff
"""


def _candidate_models():
    names = [GEMINI_MODEL, "gemini-3.0-flash", "gemini-2.5-flash", "gemini-flash-latest"]
    out = []
    for name in names:
        if name and name not in out:
            out.append(name)
    return out


def _generate(prompt):
    global _working_model
    import google.generativeai as genai

    genai.configure(api_key=GEMINI_API_KEY)
    models = [_working_model] if _working_model else _candidate_models()
    last_err = None
    for name in models:
        try:
            model = genai.GenerativeModel(name)
            response = model.generate_content(prompt)
            _working_model = name
            return getattr(response, "text", "") or ""
        except Exception as exc:
            last_err = exc
            _working_model = None
    raise last_err


def recommend(incident):
    base = fallback_note(incident)
    if not (incident.get("runbooks") or []):
        base["recommended_actions"] = []
        base["escalate"] = True
        return base
    if not GEMINI_API_KEY:
        base["llm_error"] = "GEMINI_API_KEY not set — showing runbook steps"
        return base
    try:
        parsed = _strip_json(_generate(_prompt(incident)))
        if not parsed:
            base["llm_error"] = "Gemini returned non-JSON — showing runbook steps"
            return base
        allowed = {b["id"] for b in incident.get("runbooks") or []}
        actions = []
        for item in parsed.get("recommended_actions") or []:
            rid = (item.get("source_runbook") or "").strip()
            step = (item.get("step") or "").strip()
            if step and rid in allowed:
                actions.append({"step": step, "source_runbook": rid})
        if not actions:
            actions = base["recommended_actions"]
        return {
            "summary": parsed.get("summary") or base["summary"],
            "priority": parsed.get("priority") or base["priority"],
            "recommended_actions": actions,
            "what_was_grouped": parsed.get("what_was_grouped") or base["what_was_grouped"],
            "unknowns": parsed.get("unknowns") or base["unknowns"],
            "escalate": bool(parsed.get("escalate")) or bool(incident.get("escalate")),
            "escalate_reason": parsed.get("escalate_reason") or base["escalate_reason"],
            "handoff": parsed.get("handoff") or base["handoff"],
            "llm_used": True,
        }
    except Exception as exc:
        base["llm_error"] = f"Gemini failed ({exc}) — showing runbook steps"
        return base