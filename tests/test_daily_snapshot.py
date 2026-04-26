import json, os, pytest, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from daily_snapshot import load_snapshot_data, load_prev_state

def test_load_snapshot_data_returns_expected_keys(tmp_path):
    signals = {
        "generated_at": "2026-04-26T09:00:00+00:00",
        "market": {"total_vol_24hr": 2100000, "overround": 1.014, "matched_teams": 14},
        "snapshot": {
            "Celtics": {"pm_prob": 0.184, "book_prob": 0.161, "gap": 0.023, "vol": 340000, "spread": 0.005},
            "Thunder": {"pm_prob": 0.161, "book_prob": 0.174, "gap": -0.013, "vol": 210000, "spread": 0.006},
        }
    }
    f = tmp_path / "latest_signals.json"
    f.write_text(json.dumps(signals))
    data = load_snapshot_data(str(f))
    assert data["teams"]["Celtics"]["pm_prob"] == 0.184
    assert data["market"]["total_vol_24hr"] == 2100000
    assert data["generated_at"] == "2026-04-26T09:00:00+00:00"

def test_load_snapshot_data_missing_file_raises():
    with pytest.raises(SystemExit):
        load_snapshot_data("/nonexistent/path.json")

def test_load_prev_state_returns_pm_probs(tmp_path):
    state = {
        "markets": {
            "Celtics": {"pm_prob": 0.172, "book_prob": 0.161, "gap": 0.011, "vol": 300000, "spread": 0.005},
            "Thunder": {"pm_prob": 0.169, "book_prob": 0.174, "gap": -0.005, "vol": 190000, "spread": 0.006},
        }
    }
    f = tmp_path / "state.json"
    f.write_text(json.dumps(state))
    prev = load_prev_state(str(f))
    assert prev["Celtics"] == 0.172
    assert prev["Thunder"] == 0.169

def test_load_prev_state_missing_file_returns_empty(tmp_path):
    prev = load_prev_state(str(tmp_path / "nonexistent.json"))
    assert prev == {}
