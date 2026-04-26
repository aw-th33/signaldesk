# Twitter 3-Hour Cadence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Increase Twitter posting from 0-7/day to guaranteed 8/day via 3-hour cron and 8 rotated snapshot templates that fill in when no signals fire.

**Architecture:** Extend alert_formatter.py with a snapshot tweet generator that cycles through 8 template types (readeboard, divergence radar, volume watch, market pulse, team spotlight, movers, sharp money, gap story). The engine saves previous market state so the formatter can compute probability deltas for change arrows. Twitter bot removes its skip-on-empty-signals guard so tweets always go out.

**Tech Stack:** Python 3.12, pytest, json (state persistence), tweepy (Twitter API v2)

---

## File Structure

```
Modified (4 files):
  .github/workflows/scheduler.yml      — cron 0 */4 → 0 */3
  scripts/signal_engine.py             — save prev_markets + twitter_rotation_index to state
  scripts/alert_formatter.py           — fmt_twitter_snapshot + state loading + rotation
  scripts/twitter_bot.py               — remove skip-on-no-signals guard

Created (1 file):
  tests/test_alert_formatter.py        — tests for all 8 snapshot types + edge cases

Untouched:
  scripts/orchestrator.py, scripts/telegram_bot.py, scripts/daily_snapshot.py
  scripts/build_landing.py, landing/, state.json, latest_signals.json
```

---

### Task 1: Update cron schedule

**Files:**
- Modify: `.github/workflows/scheduler.yml:5`

- [ ] **Step 1: Change cron expression**

```yaml
# line 5, change:
    - cron: "0 */4 * * *"
# to:
    - cron: "0 */3 * * *"
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/scheduler.yml
git commit -m "chore: increase tweet cadence — cron 0 */4 to 0 */3 (8 runs/day)"
```

---

### Task 2: Save previous market state in signal_engine.py

The formatter needs previous-market probabilities to compute change arrows (Leaderboard, Movers). Today the engine overwrites `state.json.markets` with current data, destroying the previous values. We'll save them under a `prev_markets` key.

**Files:**
- Modify: `scripts/signal_engine.py:112` (default state) and `scripts/signal_engine.py:328-334` (state save)

- [ ] **Step 1: Write tests for prev_markets in state**

Create `tests/test_signal_engine.py`:

```python
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
    assert state["prev_markets"] == {}
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_signal_engine.py -v
```
Expected: FAIL — `KeyError: 'prev_markets'` or assertion fails because default state doesn't have the keys.

- [ ] **Step 3: Modify signal_engine.py — update default state and persist prev_markets + twitter_rotation_index**

In `signal_engine.py`, change line 111 (the default state in `load_state`):

```python
# Before (line 111):
    return {"markets": {}, "overround": None, "vol_history": {}, "signal_history": []}
# After:
    state = {"markets": {}, "prev_markets": None, "overround": None, "vol_history": {}, "signal_history": [], "twitter_rotation_index": 0}
    # Backward compat: if file existed but was missing new keys, ensure they exist
    if "prev_markets" not in state:
        state["prev_markets"] = {}
    if "twitter_rotation_index" not in state:
        state["twitter_rotation_index"] = 0
    return state
```

Wait, that logic is wrong. `load_state` returns a hardcoded default. After loading from file, it should merge missing keys. Let me restructure:

```python
def load_state():
    defaults = {
        "markets": {},
        "prev_markets": None,
        "overround": None,
        "vol_history": {},
        "signal_history": [],
        "twitter_rotation_index": 0,
    }
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            loaded = json.load(f)
        # Merge defaults for keys that may not exist in old state files
        for key, val in defaults.items():
            loaded.setdefault(key, val)
        return loaded
    return defaults
```

Then in `main()`, where the engine saves state (lines 328-335), add `prev_markets`:

```python
# Before (line 328-335):
    new_state = {
        "last_run": now,
        "markets": new_markets,
        "overround": overround,
        "vol_history": new_vol_history,
        "signal_history": signal_history,
    }
# After:
    # Carry forward twitter_rotation_index (formatter owns this, engine preserves it)
    twitter_idx = state.get("twitter_rotation_index", 0)
    new_state = {
        "last_run": now,
        "markets": new_markets,
        "prev_markets": state.get("markets", {}) if state.get("markets") else None,
        "overround": overround,
        "vol_history": new_vol_history,
        "signal_history": signal_history,
        "twitter_rotation_index": twitter_idx,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_signal_engine.py -v
```
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_signal_engine.py scripts/signal_engine.py
git commit -m "feat: save prev_markets and twitter_rotation_index to state.json"
```

---

### Task 3: Build the snapshot tweet formatter in alert_formatter.py

**Files:**
- Create: `tests/test_alert_formatter.py`
- Modify: `scripts/alert_formatter.py`

- [ ] **Step 1: Write tests for all 8 snapshot types**

Create `tests/test_alert_formatter.py`:

```python
import json, os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from alert_formatter import (
    fmt_twitter,
    fmt_twitter_snapshot,
    _format_change_arrow,
    _pick_next_snapshot_type,
    SNAPSHOT_TYPES,
)


# Sample data matching real latest_signals.json + state.json shapes
SAMPLE_SNAPSHOT = {
    "Celtics": {"pm_prob": 0.184, "book_prob": 0.161, "gap": 0.023, "vol": 340000, "spread": 0.005},
    "Thunder": {"pm_prob": 0.161, "book_prob": 0.174, "gap": -0.013, "vol": 210000, "spread": 0.006},
    "Lakers": {"pm_prob": 0.142, "book_prob": 0.139, "gap": 0.003, "vol": 180000, "spread": 0.008},
    "Knicks": {"pm_prob": 0.091, "book_prob": 0.105, "gap": -0.014, "vol": 95000, "spread": 0.012},
    "Hornets": {"pm_prob": 0.003, "book_prob": 0.011, "gap": -0.008, "vol": 36500000, "spread": 0.050},
}

SAMPLE_MARKET = {"total_vol": 50000000, "total_vol_24hr": 4200000, "overround": 1.014, "matched_teams": 16}

SAMPLE_PREV_MARKETS = {
    "Celtics": {"pm_prob": 0.172, "book_prob": 0.161, "gap": 0.011, "vol": 300000, "vol_24hr": 45000, "spread": 0.006, "liq": 110000},
    "Thunder": {"pm_prob": 0.169, "book_prob": 0.170, "gap": -0.001, "vol": 190000, "vol_24hr": 28000, "spread": 0.005, "liq": 75000},
    "Lakers": {"pm_prob": 0.140, "book_prob": 0.141, "gap": -0.001, "vol": 170000, "vol_24hr": 35000, "spread": 0.007, "liq": 65000},
    "Knicks": {"pm_prob": 0.100, "book_prob": 0.108, "gap": -0.008, "vol": 90000, "vol_24hr": 20000, "spread": 0.010, "liq": 40000},
    "Hornets": {"pm_prob": 0.005, "book_prob": 0.010, "gap": -0.005, "vol": 36500000, "vol_24hr": 5000, "spread": 0.045, "liq": 20000},
}

NO_PREV_MARKETS = None


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
    # Types 1, 4, 7 need book_prob. If missing, skip to next valid.
    snapshot_no_book = {
        "Celtics": {"pm_prob": 0.184, "book_prob": None, "gap": None, "vol": 340000, "spread": 0.005},
    }
    # Starting at index 1 (divergence_radar, needs book), should skip to 2
    next_idx, picked = _pick_next_snapshot_type(1, snapshot_no_book)
    assert picked == 2


# --- Snapshot templates ---

def build_data(index):
    """Build full data dict for a snapshot type."""
    return {
        "index": index,
        "teams": SAMPLE_SNAPSHOT,
        "market": SAMPLE_MARKET,
        "prev_markets": SAMPLE_PREV_MARKETS,
    }


def test_fmt_twitter_snapshot_leaderboard():
    data = build_data(0)
    out = fmt_twitter_snapshot(data)
    assert "NBA Top 3" in out
    assert "Celtics" in out
    assert "Thunder" in out
    assert "Lakers" in out
    assert "↑" in out or "↓" in out or "—" in out
    assert len(out) <= 280

def test_fmt_twitter_snapshot_divergence_radar():
    data = build_data(1)
    out = fmt_twitter_snapshot(data)
    assert "PM/Books gaps" in out or "Biggest" in out
    assert len(out) <= 280

def test_fmt_twitter_snapshot_volume_watch():
    data = build_data(2)
    out = fmt_twitter_snapshot(data)
    assert "24h action" in out.lower() or "vol" in out.lower()
    assert len(out) <= 280

def test_fmt_twitter_snapshot_market_pulse():
    data = build_data(3)
    out = fmt_twitter_snapshot(data)
    assert "Overround" in out
    assert "4.2M" in out or "$4" in out
    assert len(out) <= 280

def test_fmt_twitter_snapshot_team_spotlight():
    data = build_data(4)
    out = fmt_twitter_snapshot(data)
    assert "PM" in out and "Books" in out and "Gap" in out
    assert len(out) <= 280

def test_fmt_twitter_snapshot_movers():
    data = build_data(5)
    out = fmt_twitter_snapshot(data)
    assert "move" in out.lower() or "On the move" in out
    assert len(out) <= 280

def test_fmt_twitter_snapshot_sharp_money():
    data = build_data(6)
    out = fmt_twitter_snapshot(data)
    assert "vol" in out.lower()
    assert len(out) <= 280

def test_fmt_twitter_snapshot_gap_story():
    data = build_data(7)
    out = fmt_twitter_snapshot(data)
    assert "gap" in out.lower()
    assert len(out) <= 280


# --- Edge cases ---

def test_fmt_twitter_snapshot_no_teams():
    data = {"index": 0, "teams": {}, "market": SAMPLE_MARKET, "prev_markets": None}
    out = fmt_twitter_snapshot(data)
    assert "currently sparse" in out.lower() or "standby" in out.lower()

def test_fmt_twitter_snapshot_truncates_over_280():
    # Leaderboard with many long team names
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
    assert all(chg in out for chg in ["—"])
    # No ↑ or ↓ since no previous data

def test_fmt_twitter_snapshot_sharp_money_skips_tiny_vol():
    # Teams with less than $10K vol shouldn't appear
    tiny_teams = {
        "Tiny": {"pm_prob": 0.001, "book_prob": 0.010, "gap": -0.009, "vol": 5000, "spread": 0.050},
    }
    data = {"index": 6, "teams": tiny_teams, "market": SAMPLE_MARKET, "prev_markets": None}
    out = fmt_twitter_snapshot(data)
    # Should not highlight tiny volume as "sharp money"
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
    """fmt_twitter with empty signals returns the snapshot fallback message (caller handles)."""
    meta = {"date": "Apr 26 12:00 UTC", "overround": 1.014, "matched_teams": 16}
    out = fmt_twitter([], meta)
    # Empty signals produce "Markets stable" message
    assert "stable" in out.lower() or "No triggered" in out.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_alert_formatter.py -v
```
Expected: FAIL — `ImportError: cannot import name 'fmt_twitter_snapshot'` or similar.

- [ ] **Step 3: Implement the snapshot formatter in alert_formatter.py**

Add at the top of `alert_formatter.py` (after imports, before `TYPE_PREFIX`):

```python
STATE_FILE = os.path.join(BASE_DIR, "state.json")
```

Add after `SEVERITY_LABEL` line (line 18):

```python
SNAPSHOT_TYPES = [
    "leaderboard",
    "divergence_radar",
    "volume_watch",
    "market_pulse",
    "team_spotlight",
    "movers",
    "sharp_money",
    "gap_story",
]

ODDS_DEPENDENT_TYPES = {1, 4, 7}  # indices that need book_prob
```

Add these functions before `main()`:

```python
def _format_change_arrow(current_prob, prev_prob):
    if prev_prob is None:
        return "—"
    change_pp = (current_prob - prev_prob) * 100
    if change_pp >= 0.3:
        return f"↑{change_pp:.1f}pp"
    if change_pp <= -0.3:
        return f"↓{change_pp:.1f}pp"
    return "—"


def _has_book_data(teams):
    """Check if any team in snapshot has valid book_prob."""
    for d in teams.values():
        bp = d.get("book_prob")
        if bp is not None and bp > 0:
            return True
    return False


def _pick_next_snapshot_type(current_index, teams=None):
    """Return (next_index, chosen_index) wrapping 0-7, skipping odds-types if no book data."""
    nxt = (current_index + 1) % 8
    chosen = nxt
    if teams is not None and not _has_book_data(teams):
        # Skip types that need book odds (1, 4, 7)
        while chosen in ODDS_DEPENDENT_TYPES:
            chosen = (chosen + 1) % 8
    return nxt, chosen


def fmt_twitter_snapshot(data):
    """Generate a tweet from one of 8 rotated snapshot types.

    data keys:
        index: int (0-7) — which snapshot type to use
        teams: dict — latest_signals.json snapshot
        market: dict — latest_signals.json market
        prev_markets: dict or None — state.json prev_markets (or None on first run)
    """
    teams = data.get("teams", {})
    market = data.get("market", {})
    prev_markets = data.get("prev_markets") or {}
    index = data.get("index", 0)

    if not teams:
        return "NBA champ markets currently sparse. Standby."

    sorted_by_pm = sorted(teams.items(), key=lambda x: x[1]["pm_prob"], reverse=True)

    # --- Type 0: Leaderboard ---
    if index == 0:
        top3 = sorted_by_pm[:3]
        parts = []
        for team, d in top3:
            pm_pct = d["pm_prob"] * 100
            prev = prev_markets.get(team, {}).get("pm_prob") if prev_markets else None
            arrow = _format_change_arrow(d["pm_prob"], prev)
            parts.append(f"{team} {pm_pct:.1f}% ({arrow})")
        return "NBA Top 3: " + " | ".join(parts)

    # --- Type 1: Divergence radar ---
    if index == 1:
        sorted_by_gap = sorted(teams.items(), key=lambda x: x[1]["gap"], reverse=True)
        top = sorted_by_gap[0]
        bottom = sorted_by_gap[-1]
        t1, g1 = top[0], top[1]["gap"] * 100
        t2, g2 = bottom[0], bottom[1]["gap"] * 100
        return f"Biggest PM/Books gaps: {t1} {g1:+.1f}pp above | {t2} {g2:+.1f}pp below"

    # --- Type 2: Volume watch ---
    if index == 2:
        by_vol = sorted(teams.items(), key=lambda x: x[1]["vol"], reverse=True)[:3]
        parts = []
        for team, d in by_vol:
            vol_k = d["vol"] / 1000
            parts.append(f"{team} ${vol_k:.0f}K")
        return "Most 24h action: " + " | ".join(parts)

    # --- Type 3: Market pulse ---
    if index == 3:
        ov = (market.get("overround", 1.0) - 1.0) * 100
        total_24h = market.get("total_vol_24hr", 0)
        if total_24h >= 1_000_000:
            vol_str = f"${total_24h / 1_000_000:.1f}M"
        else:
            vol_str = f"${total_24h / 1000:.0f}K"
        n = market.get("matched_teams", len(teams))
        return f"NBA champ market: Overround {ov:.1f}pp | 24h vol {vol_str} | {n} teams tracked"

    # --- Type 4: Team spotlight ---
    if index == 4:
        top = sorted_by_pm[0]
        team, d = top[0], top[1]
        pm = d["pm_prob"] * 100
        book = d["book_prob"] * 100
        gap = d["gap"] * 100
        vol_k = d["vol"] / 1000
        return f"{team}: PM {pm:.1f}% | Books {book:.1f}% | Gap {gap:+.1f}pp | 24h vol ${vol_k:.0f}K"

    # --- Type 5: Movers ---
    if index == 5:
        changes = []
        for team, d in sorted_by_pm:
            prev = prev_markets.get(team, {}).get("pm_prob") if prev_markets else None
            if prev is None:
                continue
            chg_pp = (d["pm_prob"] - prev) * 100
            if abs(chg_pp) >= 0.3:
                changes.append((team, chg_pp, d["pm_prob"] * 100))
        if not changes:
            # Fallback: show top 2 with — if no movers
            top2 = sorted_by_pm[:2]
            parts = [f"{t} {d['pm_prob']*100:.1f}% (—)" for t, d in top2]
            return "No significant moves. " + " | ".join(parts)
        top_movers = sorted(changes, key=lambda x: abs(x[1]), reverse=True)[:2]
        parts = [f"{t} {chg:+.1f}pp ({prob:.1f}%)" for t, chg, prob in top_movers]
        return "On the move: " + " | ".join(parts)

    # --- Type 6: Sharp money ---
    if index == 6:
        candidates = []
        for team, d in teams.items():
            vol = d["vol"]
            prob = d["pm_prob"]
            if vol >= 100_000 and prob <= 0.05:
                candidates.append((team, vol, prob))
        if not candidates:
            # Fallback: just show highest vol team
            top = sorted_by_pm[0]
            team, d = top[0], top[1]
            vol_k = d["vol"] / 1000
            prob = d["pm_prob"] * 100
            return f"No speculative activity. Top vol: {team} ${vol_k:.0f}K at {prob:.1f}%"
        top2 = sorted(candidates, key=lambda x: x[1], reverse=True)[:2]
        parts = [f"{t} ${v/1000:.0f}K at {p*100:.1f}%" for t, v, p in top2]
        return "High vol, low prob: " + " | ".join(parts)

    # --- Type 7: Gap story ---
    if index == 7:
        sorted_by_abs_gap = sorted(teams.items(), key=lambda x: abs(x[1]["gap"]), reverse=True)
        top = sorted_by_abs_gap[0]
        team, d = top[0], top[1]
        pm = d["pm_prob"] * 100
        book = d["book_prob"] * 100
        gap = d["gap"] * 100
        direction = "PM above books" if gap > 0 else "books above PM"
        return f"{team} {abs(gap):.1f}pp gap: PM {pm:.1f}%, books {book:.1f}%. {direction} — info edge or noise?"

    # Shouldn't reach here
    return "NBA champ markets active. Full data in bio."
```

Now modify `main()` to load state and use snapshot fallback:

```python
def main():
    if not os.path.exists(SIGNALS_FILE):
        print("No signals file found. Run signal_engine.py first.")
        sys.exit(1)

    with open(SIGNALS_FILE, encoding="utf-8") as f:
        data = json.load(f)

    # Load state.json for rotation index and previous markets
    state_data = {}
    twitter_rotation_index = 0
    prev_markets = None
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            state_data = json.load(f)
        twitter_rotation_index = state_data.get("twitter_rotation_index", 0)
        prev_markets = state_data.get("prev_markets")

    generated = data.get("generated_at", "")
    try:
        dt = datetime.fromisoformat(generated.replace("Z", "+00:00"))
        date_str = dt.strftime("%b %d %H:%M UTC")
    except Exception:
        date_str = generated

    meta = {
        "date": date_str,
        "overround": data.get("market", {}).get("overround", 0),
        "matched_teams": data.get("market", {}).get("matched_teams", 0),
    }
    signals = data.get("signals", [])
    snapshot = data.get("snapshot", {})
    market = data.get("market", {})

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    tg = fmt_telegram(signals, meta)

    # Twitter: signals if available, else snapshot rotation
    if signals:
        tw = fmt_twitter(signals, meta)
    else:
        next_idx, chosen_idx = _pick_next_snapshot_type(twitter_rotation_index, snapshot)
        tw = fmt_twitter_snapshot({
            "index": chosen_idx,
            "teams": snapshot,
            "market": market,
            "prev_markets": prev_markets,
        })
        twitter_rotation_index = next_idx

    nl = fmt_newsletter(signals, meta)

    for name, text in [("telegram", tg), ("twitter", tw), ("newsletter", nl)]:
        path = os.path.join(OUTPUT_DIR, name + ".txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print("=" * 60)
        print("[" + name.upper() + "]")
        print("=" * 60)
        print(text)
        print()

    # Save updated rotation index back to state
    if state_data is not None:
        state_data["twitter_rotation_index"] = twitter_rotation_index
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2, default=str)

    print("Written to output/telegram.txt, output/twitter.txt, output/newsletter.txt")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_alert_formatter.py -v
```
Expected: All PASS (19 tests).

- [ ] **Step 5: Run existing tests to check for regressions**

```bash
python -m pytest tests/ -v
```
Expected: All existing daily_snapshot tests still PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/test_alert_formatter.py scripts/alert_formatter.py
git commit -m "feat: snapshot tweet rotation — 8 template types, always produces content"
```

---

### Task 4: Remove skip-on-empty-signals guard from twitter_bot.py

**Files:**
- Modify: `scripts/twitter_bot.py:32-37`

- [ ] **Step 1: Remove the early-return block**

In `twitter_bot.py`, delete lines 32-37:

```python
# DELETE this block:
    if os.path.exists(SIGNALS_FILE):
        with open(SIGNALS_FILE, encoding="utf-8") as f:
            n = len(json.load(f).get("signals", []))
        if n == 0:
            print("No signals, skipping Twitter post.")
            return
```

The remaining code will check for `twitter.txt` existence and post if non-empty — which it always will be now.

- [ ] **Step 2: Commit**

```bash
git add scripts/twitter_bot.py
git commit -m "fix: remove skip-on-no-signals guard — twitter_bot always posts"
```

---

### Task 5: Full pipeline smoke test

- [ ] **Step 1: Run the orchestrator locally**

```bash
python scripts/orchestrator.py
```
Expected: All 4 steps complete. Check `output/twitter.txt` exists and contains a valid tweet <= 280 chars.

- [ ] **Step 2: Verify rotation advances across runs**

```bash
python -c "import json; s = json.load(open('state.json')); print('rotation_index:', s.get('twitter_rotation_index')); print('prev_markets has keys:', list(s.get('prev_markets', {}).keys())[:3] if s.get('prev_markets') else None)"
```
Expected: `rotation_index` is an int (0-7), `prev_markets` has team keys.

- [ ] **Step 3: Run all tests one final time**

```bash
python -m pytest tests/ -v
```
Expected: All tests PASS.

- [ ] **Step 4: Commit any remaining changes**

```bash
git status
git add -A
git commit -m "chore: final integration — pipeline smoke test passes"
```
