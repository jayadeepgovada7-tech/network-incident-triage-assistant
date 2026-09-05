import json
from src.config import DEVICES_PATH, TOPOLOGY_PATH, SAMPLES_PATH, RUNBOOKS_DIR


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_devices():
    return load_json(DEVICES_PATH)["devices"]


def load_topology():
    return load_json(TOPOLOGY_PATH)


def load_samples():
    return load_json(SAMPLES_PATH)


def load_runbooks():
    runbooks = []
    for path in sorted(RUNBOOKS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        runbook_id = "UNKNOWN"
        title = path.stem
        for line in text.splitlines():
            if line.startswith("id:"):
                runbook_id = line.split(":", 1)[1].strip()
            if line.startswith("title:"):
                title = line.split(":", 1)[1].strip()
        runbooks.append(
            {
                "id": runbook_id,
                "title": title,
                "filename": path.name,
                "text": text,
            }
        )
    return runbooks