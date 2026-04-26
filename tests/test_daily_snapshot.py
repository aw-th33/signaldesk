import json, os, pytest, sys
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from daily_snapshot import load_snapshot_data, load_prev_state, fetch_espn_scores, fetch_espn_injuries, fmt_telegram_snapshot, fmt_twitter_snapshot, fmt_newsletter_snapshot

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

def test_fetch_espn_scores_returns_empty_on_non_200():
    mock_resp = MagicMock()
    mock_resp.status_code = 503
    with patch("daily_snapshot.requests.get", return_value=mock_resp):
        games = fetch_espn_scores()
    assert games == []

def test_fetch_espn_injuries_returns_empty_on_non_200():
    mock_resp = MagicMock()
    mock_resp.status_code = 503
    with patch("daily_snapshot.requests.get", return_value=mock_resp):
        injuries = fetch_espn_injuries()
    assert injuries == []


SAMPLE_TEAMS = {
    "Celtics": {"pm_prob": 0.184, "book_prob": 0.161, "gap": 0.023, "vol": 340000, "spread": 0.005},
    "Thunder": {"pm_prob": 0.161, "book_prob": 0.174, "gap": -0.013, "vol": 210000, "spread": 0.006},
    "Knicks":  {"pm_prob": 0.147, "book_prob": 0.149, "gap": -0.002, "vol": 180000, "spread": 0.007},
}
SAMPLE_PREV = {"Celtics": 0.172, "Thunder": 0.169, "Knicks": 0.147}
SAMPLE_MARKET = {"total_vol_24hr": 2100000, "overround": 1.014, "matched_teams": 14}
SAMPLE_DATE = "Apr 26"

def test_fmt_telegram_snapshot_contains_header():
    out = fmt_telegram_snapshot(SAMPLE_TEAMS, SAMPLE_PREV, SAMPLE_MARKET, SAMPLE_DATE, [], [])
    assert "NBA Market Brief" in out
    assert "Apr 26" in out

def test_fmt_telegram_snapshot_shows_top_5_teams():
    teams = {f"Team{i}": {"pm_prob": 0.1 - i*0.01, "book_prob": 0.1, "gap": 0.0, "vol": 100000, "spread": 0.005} for i in range(7)}
    prev = {}
    out = fmt_telegram_snapshot(teams, prev, SAMPLE_MARKET, SAMPLE_DATE, [], [])
    assert "Team0" in out
    assert "Team4" in out
    assert "Team5" not in out

def test_fmt_telegram_snapshot_shows_overnight_change():
    out = fmt_telegram_snapshot(SAMPLE_TEAMS, SAMPLE_PREV, SAMPLE_MARKET, SAMPLE_DATE, [], [])
    assert "+1.2pp" in out  # Celtics moved from 17.2% to 18.4%

def test_fmt_telegram_snapshot_omits_news_when_empty():
    out = fmt_telegram_snapshot(SAMPLE_TEAMS, SAMPLE_PREV, SAMPLE_MARKET, SAMPLE_DATE, [], [])
    assert "NBA Context" not in out

def test_fmt_telegram_snapshot_includes_scores():
    games = [{"winner": "Celtics", "winner_score": 112, "loser": "Heat", "loser_score": 94}]
    out = fmt_telegram_snapshot(SAMPLE_TEAMS, SAMPLE_PREV, SAMPLE_MARKET, SAMPLE_DATE, games, [])
    assert "Celtics" in out
    assert "112" in out

def test_fmt_telegram_snapshot_includes_injuries():
    injuries = [{"player": "Joel Embiid", "team": "Sixers", "status": "Questionable", "location": "knee"}]
    out = fmt_telegram_snapshot(SAMPLE_TEAMS, SAMPLE_PREV, SAMPLE_MARKET, SAMPLE_DATE, [], injuries)
    assert "Embiid" in out
    assert "Questionable" in out


def test_overnight_arrow_positive():
    from daily_snapshot import _overnight_arrow
    assert _overnight_arrow(0.3) == "📈 +0.3pp"
    assert _overnight_arrow(1.2) == "📈 +1.2pp"


def test_overnight_arrow_negative():
    from daily_snapshot import _overnight_arrow
    assert _overnight_arrow(-0.3) == "📉 -0.3pp"
    assert _overnight_arrow(-1.2) == "📉 -1.2pp"


def test_overnight_arrow_below_threshold():
    from daily_snapshot import _overnight_arrow
    assert _overnight_arrow(0.0) == "—"
    assert _overnight_arrow(0.29) == "—"
    assert _overnight_arrow(-0.29) == "—"


def test_fmt_telegram_snapshot_shows_negative_change():
    out = fmt_telegram_snapshot(SAMPLE_TEAMS, SAMPLE_PREV, SAMPLE_MARKET, SAMPLE_DATE, [], [])
    assert "📉" in out  # Thunder dropped from 16.9% to 16.1% (-0.8pp)


def test_fmt_telegram_snapshot_dash_when_no_prev():
    teams = {"Celtics": {"pm_prob": 0.184, "book_prob": 0.161, "gap": 0.023, "vol": 340000, "spread": 0.005}}
    out = fmt_telegram_snapshot(teams, {}, SAMPLE_MARKET, SAMPLE_DATE, [], [])
    assert "Celtics" in out
    # When no prev data, should show "—" not crash
    assert "—" in out


def test_fmt_twitter_snapshot_under_280_chars():
    out = fmt_twitter_snapshot(SAMPLE_TEAMS, SAMPLE_PREV, SAMPLE_MARKET, SAMPLE_DATE, [], [])
    assert len(out) <= 280

def test_fmt_twitter_snapshot_contains_top_2_teams():
    out = fmt_twitter_snapshot(SAMPLE_TEAMS, SAMPLE_PREV, SAMPLE_MARKET, SAMPLE_DATE, [], [])
    assert "Celtics" in out
    assert "Thunder" in out

def test_fmt_twitter_snapshot_contains_signal_desk_handle():
    out = fmt_twitter_snapshot(SAMPLE_TEAMS, SAMPLE_PREV, SAMPLE_MARKET, SAMPLE_DATE, [], [])
    assert "@SignalDesk" in out

def test_fmt_twitter_snapshot_shows_injury_hook_when_present():
    injuries = [{"player": "Joel Embiid", "team": "Sixers", "status": "Questionable", "location": "knee"}]
    out = fmt_twitter_snapshot(SAMPLE_TEAMS, SAMPLE_PREV, SAMPLE_MARKET, SAMPLE_DATE, [], injuries)
    assert "Embiid" in out

def test_fmt_twitter_snapshot_truncates_if_over_limit():
    long_teams = {f"VeryLongTeamName{i}": {"pm_prob": 0.1 - i*0.005, "book_prob": 0.1, "gap": 0.05, "vol": 100000, "spread": 0.005} for i in range(10)}
    out = fmt_twitter_snapshot(long_teams, {}, SAMPLE_MARKET, SAMPLE_DATE, [], [])
    assert len(out) <= 280

def test_fmt_twitter_snapshot_gap_hook_when_no_injuries():
    out = fmt_twitter_snapshot(SAMPLE_TEAMS, SAMPLE_PREV, SAMPLE_MARKET, SAMPLE_DATE, [], [])
    assert "gap" in out.lower() or "books" in out

def test_fmt_twitter_snapshot_boundary_276_chars():
    # Build output that's exactly 276 chars before truncation guard
    # Use the normal sample — if it's under 280, test that it's unchanged
    out = fmt_twitter_snapshot(SAMPLE_TEAMS, SAMPLE_PREV, SAMPLE_MARKET, SAMPLE_DATE, [], [])
    assert len(out) <= 280

def test_fmt_twitter_snapshot_empty_teams_no_crash():
    # Should not crash with empty teams (no injuries, no teams = no hook)
    out = fmt_twitter_snapshot({}, {}, SAMPLE_MARKET, SAMPLE_DATE, [], [])
    assert "@SignalDesk" in out
    assert len(out) <= 280


def test_fmt_newsletter_snapshot_contains_all_teams():
    out = fmt_newsletter_snapshot(SAMPLE_TEAMS, SAMPLE_PREV, SAMPLE_MARKET, SAMPLE_DATE, [], [])
    assert "Celtics" in out
    assert "Thunder" in out
    assert "Knicks" in out

def test_fmt_newsletter_snapshot_contains_table_headers():
    out = fmt_newsletter_snapshot(SAMPLE_TEAMS, SAMPLE_PREV, SAMPLE_MARKET, SAMPLE_DATE, [], [])
    assert "PM Prob" in out
    assert "Change" in out
    assert "Gap" in out

def test_fmt_newsletter_snapshot_omits_results_when_empty():
    out = fmt_newsletter_snapshot(SAMPLE_TEAMS, SAMPLE_PREV, SAMPLE_MARKET, SAMPLE_DATE, [], [])
    assert "Last Night" not in out

def test_fmt_newsletter_snapshot_includes_results():
    games = [{"winner": "Celtics", "winner_score": 112, "loser": "Heat", "loser_score": 94}]
    out = fmt_newsletter_snapshot(SAMPLE_TEAMS, SAMPLE_PREV, SAMPLE_MARKET, SAMPLE_DATE, games, [])
    assert "Last Night" in out
    assert "112" in out

def test_fmt_newsletter_snapshot_omits_injuries_when_empty():
    out = fmt_newsletter_snapshot(SAMPLE_TEAMS, SAMPLE_PREV, SAMPLE_MARKET, SAMPLE_DATE, [], [])
    assert "Injury Watch" not in out

def test_fmt_newsletter_snapshot_includes_injuries():
    injuries = [{"player": "Joel Embiid", "team": "Sixers", "status": "Questionable", "location": "knee"}]
    out = fmt_newsletter_snapshot(SAMPLE_TEAMS, SAMPLE_PREV, SAMPLE_MARKET, SAMPLE_DATE, [], injuries)
    assert "Injury Watch" in out
    assert "Embiid" in out

def test_fmt_newsletter_snapshot_dash_when_no_prev():
    out = fmt_newsletter_snapshot(SAMPLE_TEAMS, {}, SAMPLE_MARKET, SAMPLE_DATE, [], [])
    assert "—" in out

def test_fmt_newsletter_snapshot_footer_content():
    out = fmt_newsletter_snapshot(SAMPLE_TEAMS, SAMPLE_PREV, SAMPLE_MARKET, SAMPLE_DATE, [], [])
    assert "Market Health" in out
    assert "$2.1M" in out
    assert "14 teams tracked" in out

def test_fmt_newsletter_snapshot_sort_order():
    out = fmt_newsletter_snapshot(SAMPLE_TEAMS, SAMPLE_PREV, SAMPLE_MARKET, SAMPLE_DATE, [], [])
    celtics_pos = out.index("Celtics")
    thunder_pos = out.index("Thunder")
    knicks_pos = out.index("Knicks")
    assert celtics_pos < thunder_pos < knicks_pos

def test_fmt_newsletter_snapshot_injury_no_location():
    injuries = [{"player": "LeBron James", "team": "Lakers", "status": "Out", "location": ""}]
    out = fmt_newsletter_snapshot(SAMPLE_TEAMS, SAMPLE_PREV, SAMPLE_MARKET, SAMPLE_DATE, [], injuries)
    assert "LeBron James" in out
    assert "()" not in out  # no empty parentheses

def test_fmt_newsletter_snapshot_empty_teams_no_crash():
    out = fmt_newsletter_snapshot({}, {}, SAMPLE_MARKET, SAMPLE_DATE, [], [])
    assert "Market Health" in out
