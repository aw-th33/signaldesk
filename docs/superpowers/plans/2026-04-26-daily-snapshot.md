# Daily NBA Market Snapshot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `scripts/daily_snapshot.py` — a daily 9am UTC script that reads existing market data and ESPN's free API to post a morning NBA brief to Telegram, Twitter, and a newsletter file.

**Architecture:** A single self-contained script reads `latest_signals.json` (snapshot + market sections) and `state.json` (for overnight change), fetches ESPN scoreboard and injuries with graceful fallback, formats three output variants at different depths, posts Telegram and Twitter directly using the same API patterns as existing bots, and saves all three to `output/`. A new GitHub Actions job triggers it daily at 9am UTC independently of the 4-hour signal engine.

**Tech Stack:** Python 3.12, requests, tweepy, Telegram Bot API, ESPN hidden JSON API (no key), GitHub Actions cache

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `scripts/daily_snapshot.py` | **Create** | All snapshot logic: data loading, ESPN fetch, formatting, posting |
| `output/snapshot_telegram.txt` | **Created at runtime** | Full Telegram brief |
| `output/snapshot_twitter.txt` | **Created at runtime** | Condensed Twitter post ≤280 chars |
| `output/snapshot_newsletter.txt` | **Created at runtime** | Full newsletter table |
| `.github/workflows/scheduler.yml` | **Modify** | Add `daily-snapshot` job at `0 9 * * *` |

---

## Task 1: Data Loading

**Files:**
- Create: `scripts/daily_snapshot.py`

- [ ] **Step 1: Write failing tests for data loading**

Create `tests/test_daily_snapshot.py`:

```python
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
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd c:\Users\admin\Documents\Polymarket
python -m pytest tests/test_daily_snapshot.py::test_load_snapshot_data_returns_expected_keys -v
```

Expected: `ModuleNotFoundError: No module named 'daily_snapshot'`

- [ ] **Step 3: Create `scripts/daily_snapshot.py` with data loading functions**

```python
import json, os, sys, io, re, time, requests
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIGNALS_FILE = os.path.join(BASE_DIR, "latest_signals.json")
STATE_FILE = os.path.join(BASE_DIR, "state.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# Load .env
env_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHANNEL = os.environ.get("TELEGRAM_CHANNEL", "")
TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY", "")
TWITTER_API_SECRET = os.environ.get("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET = os.environ.get("TWITTER_ACCESS_SECRET", "")
DRY_RUN = os.environ.get("SNAPSHOT_DRY_RUN", "0") == "1"


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
```

- [ ] **Step 4: Run tests to confirm passing**

```bash
python -m pytest tests/test_daily_snapshot.py -v -k "load"
```

Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/daily_snapshot.py tests/test_daily_snapshot.py
git commit -m "feat: daily_snapshot data loading with tests"
```

---

## Task 2: ESPN Data Fetching

**Files:**
- Modify: `scripts/daily_snapshot.py` (add ESPN fetch functions)
- Modify: `tests/test_daily_snapshot.py` (add ESPN tests)

- [ ] **Step 1: Write failing tests for ESPN fetchers**

Append to `tests/test_daily_snapshot.py`:

```python
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
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_daily_snapshot.py -v -k "espn"
```

Expected: `ImportError: cannot import name 'fetch_espn_scores'`

- [ ] **Step 3: Add ESPN fetch functions to `scripts/daily_snapshot.py`**

Append after `load_prev_state`:

```python
ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
ESPN_INJURIES = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries"


def fetch_espn_scores():
    try:
        resp = requests.get(ESPN_SCOREBOARD, timeout=10)
        if resp.status_code != 200:
            return []
        games = []
        for event in resp.json().get("events", []):
            for comp in event.get("competitions", []):
                if not comp.get("status", {}).get("type", {}).get("completed"):
                    continue
                competitors = comp.get("competitors", [])
                if len(competitors) < 2:
                    continue
                by_side = {c["homeAway"]: c for c in competitors}
                home = by_side.get("home", {})
                away = by_side.get("away", {})
                home_score = int(home.get("score", 0) or 0)
                away_score = int(away.get("score", 0) or 0)
                home_name = home.get("team", {}).get("shortDisplayName", "")
                away_name = away.get("team", {}).get("shortDisplayName", "")
                if home_score > away_score:
                    winner, w_score, loser, l_score = home_name, home_score, away_name, away_score
                else:
                    winner, w_score, loser, l_score = away_name, away_score, home_name, home_score
                games.append({"winner": winner, "winner_score": w_score, "loser": loser, "loser_score": l_score})
        return games
    except Exception as e:
        print(f"ESPN scores fetch failed: {e}")
        return []


def fetch_espn_injuries():
    try:
        resp = requests.get(ESPN_INJURIES, timeout=10)
        if resp.status_code != 200:
            return []
        injuries = []
        for team_block in resp.json().get("injuries", []):
            team_name = team_block.get("team", {}).get("shortDisplayName", "")
            for inj in team_block.get("injuries", []):
                status = inj.get("status", "")
                if status not in ("Out", "Questionable", "Doubtful"):
                    continue
                location = inj.get("details", {}).get("location", "")
                injuries.append({
                    "player": inj.get("athlete", {}).get("displayName", ""),
                    "team": team_name,
                    "status": status,
                    "location": location,
                })
        return injuries
    except Exception as e:
        print(f"ESPN injuries fetch failed: {e}")
        return []
```

- [ ] **Step 4: Run tests to confirm passing**

```bash
python -m pytest tests/test_daily_snapshot.py -v -k "espn"
```

Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/daily_snapshot.py tests/test_daily_snapshot.py
git commit -m "feat: ESPN scores and injuries fetch with graceful fallback"
```

---

## Task 3: Formatting — Telegram

**Files:**
- Modify: `scripts/daily_snapshot.py` (add `fmt_telegram_snapshot`)
- Modify: `tests/test_daily_snapshot.py` (add format tests)

- [ ] **Step 1: Write failing test**

Append to `tests/test_daily_snapshot.py`:

```python
from daily_snapshot import fmt_telegram_snapshot

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
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_daily_snapshot.py -v -k "telegram"
```

Expected: `ImportError: cannot import name 'fmt_telegram_snapshot'`

- [ ] **Step 3: Add `fmt_telegram_snapshot` to `scripts/daily_snapshot.py`**

Append after ESPN functions:

```python
def _overnight_arrow(change_pp):
    if change_pp >= 0.3:
        return f"📈 +{change_pp:.1f}pp"
    if change_pp <= -0.3:
        return f"📉 {change_pp:.1f}pp"
    return "—"


def fmt_telegram_snapshot(teams, prev_probs, market, date_str, games, injuries):
    lines = [f"📊 NBA Market Brief — {date_str}", ""]
    lines.append("🏆 Championship Odds (Polymarket)")

    sorted_teams = sorted(teams.items(), key=lambda x: x[1]["pm_prob"], reverse=True)
    for i, (team, d) in enumerate(sorted_teams[:5], 1):
        pm = d["pm_prob"] * 100
        book = d["book_prob"] * 100
        gap = d["gap"] * 100
        prev = prev_probs.get(team)
        change_pp = (d["pm_prob"] - prev) * 100 if prev is not None else None
        arrow = _overnight_arrow(change_pp) if change_pp is not None else "—"
        gap_str = f"{gap:+.1f}pp"
        lines.append(f"{i}. {team:<12} {pm:.1f}%  {arrow:<14} | Books: {book:.1f}%  GAP: {gap_str}")

    if games or injuries:
        lines.append("")
        lines.append("📰 NBA Context")
        for g in games:
            lines.append(f"• {g['winner']} def. {g['loser']} {g['winner_score']}-{g['loser_score']}")
        for inj in injuries:
            loc = f" ({inj['location']})" if inj["location"] else ""
            lines.append(f"• {inj['player']}{loc} listed {inj['status']} — {inj['team']}")

    lines.append("")
    lines.append("📊 Market Health")
    vol_m = market.get("total_vol_24hr", 0) / 1_000_000
    overround_pp = (market.get("overround", 1.0) - 1.0) * 100
    tracked = market.get("matched_teams", "?")
    lines.append(f"24h vol: ${vol_m:.1f}M | Overround: {overround_pp:.1f}pp | Markets tracked: {tracked}")

    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to confirm passing**

```bash
python -m pytest tests/test_daily_snapshot.py -v -k "telegram"
```

Expected: 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/daily_snapshot.py tests/test_daily_snapshot.py
git commit -m "feat: Telegram snapshot formatter"
```

---

## Task 4: Formatting — Twitter

**Files:**
- Modify: `scripts/daily_snapshot.py` (add `fmt_twitter_snapshot`)
- Modify: `tests/test_daily_snapshot.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_daily_snapshot.py`:

```python
from daily_snapshot import fmt_twitter_snapshot

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
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_daily_snapshot.py -v -k "twitter"
```

Expected: `ImportError: cannot import name 'fmt_twitter_snapshot'`

- [ ] **Step 3: Add `fmt_twitter_snapshot` to `scripts/daily_snapshot.py`**

Append after `fmt_telegram_snapshot`:

```python
def fmt_twitter_snapshot(teams, prev_probs, market, date_str, games, injuries):
    sorted_teams = sorted(teams.items(), key=lambda x: x[1]["pm_prob"], reverse=True)
    top2 = sorted_teams[:2]

    lines = [f"NBA Markets — {date_str}", ""]

    team_parts = []
    for team, d in top2:
        pm = d["pm_prob"] * 100
        prev = prev_probs.get(team)
        change_str = ""
        if prev is not None:
            chg = (d["pm_prob"] - prev) * 100
            if abs(chg) >= 0.3:
                change_str = f" ({chg:+.1f}pp)"
        team_parts.append(f"{team} {pm:.1f}%{change_str}")
    lines.append(" | ".join(team_parts))

    # News hook: injury if available, otherwise biggest gap
    hook = ""
    if injuries:
        inj = injuries[0]
        loc = f" ({inj['location']})" if inj["location"] else ""
        hook = f"{inj['player']}{loc} {inj['status']} → {inj['team']} watch"
    else:
        biggest_gap_team = max(teams.items(), key=lambda x: abs(x[1]["gap"]))
        team_name, d = biggest_gap_team
        gap_pp = d["gap"] * 100
        direction = "above" if gap_pp > 0 else "below"
        hook = f"Biggest gap: {team_name} {abs(gap_pp):.1f}pp {direction} books"

    if hook:
        lines.append("")
        lines.append(hook)

    lines.append("")
    lines.append("Signal Desk on Telegram 👇 @SignalDesk")

    out = "\n".join(lines)
    if len(out) > 275:
        out = out[:274] + "…"
    return out
```

- [ ] **Step 4: Run tests to confirm passing**

```bash
python -m pytest tests/test_daily_snapshot.py -v -k "twitter"
```

Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/daily_snapshot.py tests/test_daily_snapshot.py
git commit -m "feat: Twitter snapshot formatter"
```

---

## Task 5: Formatting — Newsletter

**Files:**
- Modify: `scripts/daily_snapshot.py` (add `fmt_newsletter_snapshot`)
- Modify: `tests/test_daily_snapshot.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_daily_snapshot.py`:

```python
from daily_snapshot import fmt_newsletter_snapshot

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
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_daily_snapshot.py -v -k "newsletter"
```

Expected: `ImportError: cannot import name 'fmt_newsletter_snapshot'`

- [ ] **Step 3: Add `fmt_newsletter_snapshot` to `scripts/daily_snapshot.py`**

Append after `fmt_twitter_snapshot`:

```python
def fmt_newsletter_snapshot(teams, prev_probs, market, date_str, games, injuries):
    lines = [f"## NBA Championship Markets — {date_str}", ""]
    lines.append("| Team | PM Prob | Change | Books | Gap | 24h Vol |")
    lines.append("|------|---------|--------|-------|-----|---------|")

    sorted_teams = sorted(teams.items(), key=lambda x: x[1]["pm_prob"], reverse=True)
    for team, d in sorted_teams:
        pm = d["pm_prob"] * 100
        book = d["book_prob"] * 100
        gap = d["gap"] * 100
        vol_k = d["vol"] / 1000
        prev = prev_probs.get(team)
        if prev is not None:
            chg = (d["pm_prob"] - prev) * 100
            change_str = f"{chg:+.1f}pp"
        else:
            change_str = "—"
        lines.append(f"| {team} | {pm:.1f}% | {change_str} | {book:.1f}% | {gap:+.1f}pp | ${vol_k:.0f}K |")

    if games:
        lines.append("")
        lines.append("### Last Night's Results")
        for g in games:
            lines.append(f"- {g['winner']} {g['winner_score']} def. {g['loser']} {g['loser_score']}")

    if injuries:
        lines.append("")
        lines.append("### Injury Watch")
        for inj in injuries:
            loc = f" ({inj['location']})" if inj["location"] else ""
            lines.append(f"- {inj['player']} ({inj['team']}) — {inj['status']}{loc}")

    lines.append("")
    vol_m = market.get("total_vol_24hr", 0) / 1_000_000
    overround_pp = (market.get("overround", 1.0) - 1.0) * 100
    tracked = market.get("matched_teams", "?")
    lines.append(f"**Market Health:** 24h vol ${vol_m:.1f}M | Overround {overround_pp:.1f}pp | {tracked} teams tracked")

    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to confirm passing**

```bash
python -m pytest tests/test_daily_snapshot.py -v -k "newsletter"
```

Expected: 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/daily_snapshot.py tests/test_daily_snapshot.py
git commit -m "feat: newsletter snapshot formatter"
```

---

## Task 6: Posting and `main()`

**Files:**
- Modify: `scripts/daily_snapshot.py` (add posting + main)

- [ ] **Step 1: Write failing test for dry-run main**

Append to `tests/test_daily_snapshot.py`:

```python
from unittest.mock import patch, MagicMock

def test_main_dry_run_writes_output_files(tmp_path):
    signals = {
        "generated_at": "2026-04-26T09:00:00+00:00",
        "market": {"total_vol_24hr": 2100000, "overround": 1.014, "matched_teams": 14},
        "snapshot": {
            "Celtics": {"pm_prob": 0.184, "book_prob": 0.161, "gap": 0.023, "vol": 340000, "spread": 0.005},
        }
    }
    state = {"markets": {"Celtics": {"pm_prob": 0.172, "book_prob": 0.161, "gap": 0.011, "vol": 300000, "spread": 0.005}}}
    sig_file = tmp_path / "latest_signals.json"
    state_file = tmp_path / "state.json"
    out_dir = tmp_path / "output"
    sig_file.write_text(json.dumps(signals))
    state_file.write_text(json.dumps(state))

    import daily_snapshot as ds
    with patch.object(ds, "SIGNALS_FILE", str(sig_file)), \
         patch.object(ds, "STATE_FILE", str(state_file)), \
         patch.object(ds, "OUTPUT_DIR", str(out_dir)), \
         patch.object(ds, "DRY_RUN", True), \
         patch("daily_snapshot.fetch_espn_scores", return_value=[]), \
         patch("daily_snapshot.fetch_espn_injuries", return_value=[]):
        ds.main()

    assert (out_dir / "snapshot_telegram.txt").exists()
    assert (out_dir / "snapshot_twitter.txt").exists()
    assert (out_dir / "snapshot_newsletter.txt").exists()
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_daily_snapshot.py::test_main_dry_run_writes_output_files -v
```

Expected: `AttributeError: module 'daily_snapshot' has no attribute 'main'`

- [ ] **Step 3: Add posting functions and `main()` to `scripts/daily_snapshot.py`**

Append after `fmt_newsletter_snapshot`:

```python
def post_telegram(text):
    if not BOT_TOKEN or not CHANNEL:
        print("Telegram credentials not set, skipping.")
        return
    escaped = text.replace("&", "&amp;").replace("<", "&lt;")
    if DRY_RUN:
        print(f"[DRY RUN] Telegram ({len(escaped)} chars):\n{text}\n")
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": CHANNEL, "text": escaped,
            "parse_mode": "HTML", "disable_web_page_preview": True,
        }, timeout=15)
        data = resp.json()
        if not data.get("ok"):
            print(f"Telegram error: {data.get('description', 'unknown')}")
        else:
            print(f"Telegram posted. Message ID: {data['result']['message_id']}")
    except Exception as e:
        print(f"Telegram post failed: {e}")


def post_twitter(text):
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET]):
        print("Twitter credentials not set, skipping.")
        return
    if DRY_RUN:
        print(f"[DRY RUN] Twitter ({len(text)} chars):\n{text}\n")
        return
    try:
        import tweepy
        client = tweepy.Client(
            consumer_key=TWITTER_API_KEY, consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN, access_token_secret=TWITTER_ACCESS_SECRET,
        )
        resp = client.create_tweet(text=text)
        print(f"Twitter posted. Tweet ID: {resp.data['id']}")
    except Exception as e:
        print(f"Twitter post failed: {e}")


def main():
    t0 = time.time()
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%b %-d") if os.name != "nt" else now.strftime("%b %d").lstrip("0")
    print(f"Signal Desk Daily Snapshot — {now.isoformat()}")
    print("-" * 55)

    data = load_snapshot_data()
    prev_probs = load_prev_state()

    print("Fetching ESPN data...")
    games = fetch_espn_scores()
    injuries = fetch_espn_injuries()
    print(f"  Games: {len(games)} | Injuries: {len(injuries)}")

    teams = data["teams"]
    market = data["market"]

    tg = fmt_telegram_snapshot(teams, prev_probs, market, date_str, games, injuries)
    tw = fmt_twitter_snapshot(teams, prev_probs, market, date_str, games, injuries)
    nl = fmt_newsletter_snapshot(teams, prev_probs, market, date_str, games, injuries)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for fname, content in [
        ("snapshot_telegram.txt", tg),
        ("snapshot_twitter.txt", tw),
        ("snapshot_newsletter.txt", nl),
    ]:
        path = os.path.join(OUTPUT_DIR, fname)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Written: {path}")

    print("\nPosting...")
    post_telegram(tg)
    post_twitter(tw)

    print(f"\nDone in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run all tests to confirm passing**

```bash
python -m pytest tests/test_daily_snapshot.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Smoke test in dry-run mode**

```bash
cd c:\Users\admin\Documents\Polymarket
SNAPSHOT_DRY_RUN=1 python scripts/daily_snapshot.py
```

On Windows use:
```bash
set SNAPSHOT_DRY_RUN=1 && python scripts/daily_snapshot.py
```

Expected: Prints formatted output for all three channels, writes three files to `output/`, no API calls made.

- [ ] **Step 6: Commit**

```bash
git add scripts/daily_snapshot.py tests/test_daily_snapshot.py
git commit -m "feat: daily snapshot posting and main entrypoint"
```

---

## Task 7: GitHub Actions Schedule

**Files:**
- Modify: `.github/workflows/scheduler.yml`

- [ ] **Step 1: Add `daily-snapshot` job to workflow**

Open `.github/workflows/scheduler.yml` and append the following job inside the `jobs:` block (same indentation level as `run:`):

```yaml
  daily-snapshot:
    runs-on: ubuntu-latest
    timeout-minutes: 5

    env:
      TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
      TELEGRAM_CHANNEL: ${{ secrets.TELEGRAM_CHANNEL }}
      TWITTER_API_KEY: ${{ secrets.TWITTER_API_KEY }}
      TWITTER_API_SECRET: ${{ secrets.TWITTER_API_SECRET }}
      TWITTER_ACCESS_TOKEN: ${{ secrets.TWITTER_ACCESS_TOKEN }}
      TWITTER_ACCESS_SECRET: ${{ secrets.TWITTER_ACCESS_SECRET }}

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Restore signal state
        uses: actions/cache/restore@v4
        with:
          path: |
            state.json
            latest_signals.json
          key: apex-state-${{ github.run_number }}
          restore-keys: apex-state-

      - name: Run daily snapshot
        run: python scripts/daily_snapshot.py
```

Also update the `on:` block at the top to add the 9am trigger:

```yaml
on:
  schedule:
    - cron: "0 */4 * * *"
    - cron: "0 9 * * *"
  workflow_dispatch:
```

- [ ] **Step 2: Verify the YAML is valid**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/scheduler.yml'))"
```

Expected: No output (clean parse)

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/scheduler.yml
git commit -m "feat: add daily snapshot job to GitHub Actions at 9am UTC"
```

---

## Task 8: Full Integration Verification

- [ ] **Step 1: Run the full test suite**

```bash
python -m pytest tests/test_daily_snapshot.py -v
```

Expected: All tests PASS, 0 failures

- [ ] **Step 2: Run live dry-run against real data**

Ensure `latest_signals.json` and `state.json` exist (run `python scripts/signal_engine.py` if not), then:

```bash
set SNAPSHOT_DRY_RUN=1 && python scripts/daily_snapshot.py
```

Verify:
- Output shows real team names and probabilities
- Overnight changes shown correctly (or `—` if state is missing)
- ESPN section appears if there were games/injuries today
- All three files written to `output/`
- Twitter output is ≤280 chars (check the printed char count)

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: daily NBA snapshot complete — Telegram, Twitter, newsletter"
```
