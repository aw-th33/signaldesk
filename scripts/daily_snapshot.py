import json, os, sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIGNALS_FILE = os.path.join(BASE_DIR, "latest_signals.json")
STATE_FILE = os.path.join(BASE_DIR, "state.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")



def load_snapshot_data(path=None):
    path = path or SIGNALS_FILE
    if not os.path.exists(path):
        print("latest_signals.json not found. Run signal_engine.py first.")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return {
        "generated_at": raw.get("generated_at", ""),
        "market": raw.get("market", {}),
        "teams": raw.get("snapshot", {}),
    }


def load_prev_state(path=None):
    path = path or STATE_FILE
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        state = json.load(f)
    return {
        team: data["pm_prob"]
        for team, data in state.get("markets", {}).items()
        if "pm_prob" in data
    }
