import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RUNBOOKS_DIR = DATA_DIR / "runbooks"

DEVICES_PATH = DATA_DIR / "devices.json"
TOPOLOGY_PATH = DATA_DIR / "topology.json"
SAMPLES_PATH = DATA_DIR / "sample_alerts.json"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.0-flash")