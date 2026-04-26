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
    f.write_text(json.dumps(signals), encoding="utf-8")
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
    f.write_text(json.dumps(state), encoding="utf-8")
    prev = load_prev_state(str(f))
    assert prev["Celtics"] == 0.172
    assert prev["Thunder"] == 0.169

def test_load_prev_state_missing_file_returns_empty(tmp_path):
    prev = load_prev_state(str(tmp_path / "nonexistent.json"))
    assert prev == {}

from unittest.mock import patch, MagicMock
from daily_snapshot import fetch_espn_scores, fetch_espn_injuries

def test_fetch_espn_scores_returns_list_of_games():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "events": [
            {
                "competitions": [{
                    "competitors": [
                        {"homeAway": "home", "team": {"shortDisplayName": "Celtics"}, "score": "112"},
                        {"homeAway": "away", "team": {"shortDisplayName": "Heat"}, "score": "94"},
                    ],
                    "status": {"type": {"completed": True}}
                }]
            }
        ]
    }
    with patch("daily_snapshot.requests.get", return_value=mock_resp):
        games = fetch_espn_scores()
    assert len(games) == 1
    assert games[0]["winner"] == "Celtics"
    assert games[0]["winner_score"] == 112
    assert games[0]["loser"] == "Heat"
    assert games[0]["loser_score"] == 94

def test_fetch_espn_scores_returns_empty_on_failure():
    with patch("daily_snapshot.requests.get", side_effect=Exception("timeout")):
        games = fetch_espn_scores()
    assert games == []

def test_fetch_espn_injuries_returns_list():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "injuries": [
            {
                "team": {"shortDisplayName": "Sixers"},
                "injuries": [
                    {"athlete": {"displayName": "Joel Embiid"}, "status": "Questionable", "details": {"location": "knee"}}
                ]
            }
        ]
    }
    with patch("daily_snapshot.requests.get", return_value=mock_resp):
        injuries = fetch_espn_injuries()
    assert len(injuries) == 1
    assert injuries[0]["player"] == "Joel Embiid"
    assert injuries[0]["team"] == "Sixers"
    assert injuries[0]["status"] == "Questionable"
    assert injuries[0]["location"] == "knee"

def test_fetch_espn_injuries_returns_empty_on_failure():
    with patch("daily_snapshot.requests.get", side_effect=Exception("timeout")):
        injuries = fetch_espn_injuries()
    assert injuries == []
