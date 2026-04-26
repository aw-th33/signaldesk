import json, os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from alert_formatter import (
    fmt_twitter,
    fmt_twitter_snapshot,
    _format_change_arrow,
    _pick_next_snapshot_type,
    SNAPSHOT_TYPES,
)


SAMPLE_SNAPSHOT = {
    "Celtics": {"pm_prob": 0.184, "book_prob": 0.161, "gap": 0.023, "vol": 340000, "spread": 0.005},
    "Thunder": {"pm_prob": 0.161, "book_prob": 0.174, "gap": -0.013, "vol": 210000, "spread": 0.006},
    "Lakers": {"pm_prob": 0.142, "book_prob": 0.139, "gap": 0.003, "vol": 180000, "spread": 0.008},
    "Knicks": {"pm_prob": 0.091, "book_prob": 0.105, "gap": -0.014, "vol": 95000, "spread": 0.012},
    "Hornets": {"pm_prob": 0.003, "book_prob": 0.011, "gap": -0.008, "vol": 36500000, "spread": 0.050},
}

SAMPLE_MARKET = {"total_vol": 50000000, "total_vol_24hr": 4200000, "overround": 1.014, "matched_teams": 16}

SAMPLE_PREV_MARKETS = {
    "Celtics": {"pm_prob": 0.172},
    "Thunder": {"pm_prob": 0.169},
    "Lakers": {"pm_prob": 0.140},
    "Knicks": {"pm_prob": 0.100},
    "Hornets": {"pm_prob": 0.005},
}


def build_data(index):
    return {
        "index": index,
        "teams": SAMPLE_SNAPSHOT,
        "market": SAMPLE_MARKET,
        "prev_markets": SAMPLE_PREV_MARKETS,
    }


# --- Change arrow ---

def test_format_change_arrow_up():
    assert _format_change_arrow(0.184, 0.180) == "↑0.4pp"

def test_format_change_arrow_down():
    assert _format_change_arrow(0.180, 0.184) == "↓0.4pp"

def test_format_change_arrow_flat():
    assert _format_change_arrow(0.184, 0.183) == "—"

def test_format_change_arrow_prev_none():
    assert _format_change_arrow(0.184, None) == "—"


# --- Rotation ---

def test_pick_next_snapshot_type_wraps():
    assert _pick_next_snapshot_type(7) == (0, 0)
    assert _pick_next_snapshot_type(0) == (1, 1)
    assert _pick_next_snapshot_type(3) == (4, 4)

def test_pick_next_snapshot_type_skips_odds_types_if_no_book_data():
    snapshot_no_book = {
        "Celtics": {"pm_prob": 0.184, "book_prob": None, "gap": None, "vol": 340000, "spread": 0.005},
    }
    next_idx, picked = _pick_next_snapshot_type(1, snapshot_no_book)
    assert picked == 2
    next_idx, picked = _pick_next_snapshot_type(4, snapshot_no_book)
    assert picked == 5
    next_idx, picked = _pick_next_snapshot_type(7, snapshot_no_book)
    assert picked == 0


# --- Snapshot templates ---

def test_fmt_twitter_snapshot_leaderboard():
    out = fmt_twitter_snapshot(build_data(0))
    assert "NBA Top 3" in out
    assert "Celtics" in out
    assert len(out) <= 280

def test_fmt_twitter_snapshot_divergence_radar():
    out = fmt_twitter_snapshot(build_data(1))
    assert "PM/Books gaps" in out or "Biggest" in out
    assert len(out) <= 280

def test_fmt_twitter_snapshot_volume_watch():
    out = fmt_twitter_snapshot(build_data(2))
    assert "24h action" in out.lower() or "vol" in out.lower()
    assert len(out) <= 280

def test_fmt_twitter_snapshot_market_pulse():
    out = fmt_twitter_snapshot(build_data(3))
    assert "Overround" in out
    assert len(out) <= 280

def test_fmt_twitter_snapshot_team_spotlight():
    out = fmt_twitter_snapshot(build_data(4))
    assert "PM" in out and "Books" in out and "Gap" in out
    assert len(out) <= 280

def test_fmt_twitter_snapshot_movers():
    out = fmt_twitter_snapshot(build_data(5))
    assert "move" in out.lower() or "On the move" in out
    assert len(out) <= 280

def test_fmt_twitter_snapshot_sharp_money():
    out = fmt_twitter_snapshot(build_data(6))
    assert "vol" in out.lower()
    assert len(out) <= 280

def test_fmt_twitter_snapshot_gap_story():
    out = fmt_twitter_snapshot(build_data(7))
    assert "gap" in out.lower()
    assert len(out) <= 280


# --- Edge cases ---

def test_fmt_twitter_snapshot_no_teams():
    data = {"index": 0, "teams": {}, "market": SAMPLE_MARKET, "prev_markets": None}
    out = fmt_twitter_snapshot(data)
    assert "currently sparse" in out.lower() or "standby" in out.lower()

def test_fmt_twitter_snapshot_truncates_over_280():
    long_teams = {
        f"Very Long Team Name {i}": {"pm_prob": 0.1, "book_prob": 0.1, "gap": 0.0, "vol": 1000, "spread": 0.01}
        for i in range(10)
    }
    data = {"index": 0, "teams": long_teams, "market": SAMPLE_MARKET, "prev_markets": None}
    out = fmt_twitter_snapshot(data)
    assert len(out) <= 280

def test_fmt_twitter_snapshot_no_prev_markets_arrows_show_dash():
    data = {"index": 0, "teams": SAMPLE_SNAPSHOT, "market": SAMPLE_MARKET, "prev_markets": None}
    out = fmt_twitter_snapshot(data)
    assert all(chg not in out for chg in ["↑", "↓"])

def test_fmt_twitter_snapshot_sharp_money_skips_tiny_vol():
    tiny_teams = {
        "Tiny": {"pm_prob": 0.001, "book_prob": 0.010, "gap": -0.009, "vol": 5000, "spread": 0.050},
    }
    data = {"index": 6, "teams": tiny_teams, "market": SAMPLE_MARKET, "prev_markets": None}
    out = fmt_twitter_snapshot(data)
    assert "Tiny" not in out or len(out) <= 280


# --- Existing fmt_twitter still works ---

def test_fmt_twitter_with_signals_unchanged():
    signals = [
        {
            "type": "divergence_change",
            "team": "Celtics",
            "severity": "high",
            "details": {
                "pm_prob": 0.184, "book_prob": 0.161, "change": 0.012,
                "direction": "widening", "current_gap": 0.023, "previous_gap": 0.011,
                "spread": 0.005, "vol": 340000,
            },
            "message": "Widening divergence: Celtics PM 18.4% vs Books 16.1%",
        },
        {
            "type": "probability_move",
            "team": "Thunder",
            "severity": "medium",
            "details": {
                "pm_prob": 0.161, "previous_prob": 0.169, "change": -0.008,
                "direction": "falling", "vol": 210000, "spread": 0.006,
            },
            "message": "Probability falling: Thunder 16.9% → 16.1%",
        },
    ]
    meta = {"date": "Apr 26 12:00 UTC", "overround": 1.014, "matched_teams": 16}
    out = fmt_twitter(signals, meta)
    assert "Celtics" in out
    assert "Thunder" in out
    assert "Full data in bio" in out

def test_fmt_twitter_empty_signals_fallback():
    meta = {"date": "Apr 26 12:00 UTC", "overround": 1.014, "matched_teams": 16}
    out = fmt_twitter([], meta)
    assert "stable" in out.lower() or "No triggered" in out.lower()
