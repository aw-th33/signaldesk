import json, os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from signal_engine import load_state, save_state


def test_load_state_default_includes_prev_markets_and_rotation(tmp_path, monkeypatch):
    """When no state file exists, default includes prev_markets=None and twitter_rotation_index=0."""
    nonexistent = tmp_path / "nonexistent.json"
    monkeypatch.setattr("signal_engine.STATE_FILE", str(nonexistent))

    state = load_state()
    assert state["prev_markets"] is None
    assert state["twitter_rotation_index"] == 0


def test_load_state_merges_missing_keys_from_default(tmp_path, monkeypatch):
    """Old state files missing prev_markets/twitter_rotation_index get defaults on load."""
    state_file = tmp_path / "state.json"
    old_state = {"markets": {"Celtics": {"pm_prob": 0.5, "book_prob": 0.45, "gap": 0.05, "vol": 300000, "vol_24hr": 40000, "spread": 0.005, "liq": 100000}}, "overround": 1.0, "vol_history": {}, "signal_history": []}
    state_file.write_text(json.dumps(old_state), encoding="utf-8")
    monkeypatch.setattr("signal_engine.STATE_FILE", str(state_file))

    state = load_state()
    assert state["prev_markets"] is None
    assert state["twitter_rotation_index"] == 0
    assert state["markets"]["Celtics"]["pm_prob"] == 0.5


def test_save_state_persists_all_keys(tmp_path, monkeypatch):
    """After save, load returns all keys including prev_markets and twitter_rotation_index."""
    state_file = tmp_path / "state.json"
    monkeypatch.setattr("signal_engine.STATE_FILE", str(state_file))

    state1 = {
        "last_run": "2026-01-01T00:00:00Z",
        "markets": {"Celtics": {"pm_prob": 0.184, "book_prob": 0.161, "gap": 0.023, "vol": 340000, "vol_24hr": 50000, "spread": 0.005, "liq": 120000}},
        "prev_markets": None,
        "overround": 1.014,
        "vol_history": {},
        "signal_history": [],
        "twitter_rotation_index": 0,
    }
    save_state(state1)

    loaded = load_state()
    assert loaded["prev_markets"] is None
    assert loaded["twitter_rotation_index"] == 0
    assert loaded["markets"]["Celtics"]["pm_prob"] == 0.184


def test_prev_markets_captures_previous_run_data(tmp_path, monkeypatch):
    """Simulate two engine runs: after second run, prev_markets = first run's markets."""
    state_file = tmp_path / "state.json"
    monkeypatch.setattr("signal_engine.STATE_FILE", str(state_file))

    # Run 1: initial state
    state1 = {
        "last_run": "2026-01-01T00:00:00Z",
        "markets": {
            "Celtics": {"pm_prob": 0.184, "book_prob": 0.161, "gap": 0.023, "vol": 340000, "vol_24hr": 50000, "spread": 0.005, "liq": 120000},
        },
        "prev_markets": None,
        "overround": 1.014,
        "vol_history": {},
        "signal_history": [],
        "twitter_rotation_index": 3,
    }
    save_state(state1)

    # Run 2: engine reads old, saves new with prev_markets from old markets
    old = load_state()
    state2 = {
        "last_run": "2026-01-01T03:00:00Z",
        "markets": {
            "Celtics": {"pm_prob": 0.200, "book_prob": 0.165, "gap": 0.035, "vol": 360000, "vol_24hr": 52000, "spread": 0.004, "liq": 130000},
        },
        "prev_markets": old["markets"],
        "overround": 1.016,
        "vol_history": {},
        "signal_history": [],
        "twitter_rotation_index": old.get("twitter_rotation_index", 0),
    }
    save_state(state2)

    reloaded = load_state()
    assert reloaded["markets"]["Celtics"]["pm_prob"] == 0.200
    assert reloaded["prev_markets"]["Celtics"]["pm_prob"] == 0.184
    assert reloaded["twitter_rotation_index"] == 3
