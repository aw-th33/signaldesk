# Daily NBA Market Snapshot — Design Spec

**Date:** 2026-04-26
**Status:** Approved

## Overview

A new script `scripts/daily_snapshot.py` that produces a daily morning brief across three channels (Telegram, Twitter, Newsletter). It runs on a fixed 9am UTC schedule independent of the event-driven signal engine. It combines championship market data already on disk with live NBA context from ESPN's free hidden API.

---

## Data Sources

### 1. `latest_signals.json` (on disk, no API call)
- `snapshot` section: all matched teams with `pm_prob`, `book_prob`, `gap`, `vol`, `spread`
- `market` section: `total_vol_24hr`, `overround`, `matched_teams`

### 2. `state.json` (on disk, read-only)
- `markets` section: previous `pm_prob` per team — used to compute overnight probability change (`change = current - previous`)

### 3. ESPN Hidden API (free, no key, no account)
- Scores: `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard`
  - Returns yesterday's completed games: home team, away team, scores
- Injuries: `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries`
  - Returns active injury reports: player name, team, status (Out/Questionable/Doubtful)

**Fallback:** If either ESPN endpoint fails or returns no data, the snapshot posts without that section rather than failing entirely.

---

## Output Files

| File | Channel | Depth |
|------|---------|-------|
| `output/snapshot_telegram.txt` | Telegram | Full brief |
| `output/snapshot_twitter.txt` | Twitter/X | Condensed, ≤280 chars |
| `output/snapshot_newsletter.txt` | Beehiiv (future) | Full table + context |

---

## Output Formats

### Telegram (full brief)
```
📊 NBA Market Brief — Apr 26

🏆 Championship Odds (Polymarket)
1. Celtics    18.4%  📈 +1.2pp  | Books: 16.1%  GAP: +2.3pp
2. Thunder    16.1%  📉 -0.8pp  | Books: 17.4%  GAP: -1.3pp
3. Knicks     14.7%   —         | Books: 14.9%  GAP: -0.2pp
...

📰 NBA Context
• Celtics def. Heat 112-94 — odds moved +1.2pp overnight
• Embiid (knee) listed questionable — Sixers down 0.8pp on PM

📊 Market Health
24h vol: $2.1M | Overround: 1.4% | Markets tracked: 14
```

Rules:
- Teams sorted by `pm_prob` descending
- Show top 5 teams in the odds table, remaining teams omitted
- Overnight change shown as `📈 +Xpp` / `📉 -Xpp` / `—` (if <0.3pp move)
- GAP = `pm_prob - book_prob`, positive means PM is higher than books
- News section omitted entirely if ESPN returns no data
- Each score result linked to the team's championship odds move if team name matches

### Twitter (condensed, ≤280 chars)
```
NBA Markets — Apr 26

Celtics 18.4% (+1.2pp) | Thunder 16.1% (-0.8pp)
Biggest gap: Celtics +2.3pp above books

Embiid questionable → Sixers slipping on PM

Signal Desk on Telegram 👇
```

Rules:
- Top 2 teams by `pm_prob` only
- One news hook: either biggest gap OR most notable injury (whichever is more interesting — biggest gap if no injuries, injury if one exists)
- Telegram handle `@SignalDesk` appended as final line
- Hard truncate at 275 chars with `…` if over limit

### Newsletter (full table)
```
## NBA Championship Markets — Apr 26

| Team      | PM Prob | Change  | Books  | Gap    | 24h Vol  |
|-----------|---------|---------|--------|--------|----------|
| Celtics   | 18.4%   | +1.2pp  | 16.1%  | +2.3pp | $340K    |
| Thunder   | 16.1%   | -0.8pp  | 17.4%  | -1.3pp | $210K    |
| ...       | ...     | ...     | ...    | ...    | ...      |

### Last Night's Results
- Celtics 112 def. Heat 94
- Thunder 108 def. Lakers 101

### Injury Watch
- Joel Embiid (PHI) — Questionable (knee)
- Ja Morant (MEM) — Out (shoulder)

**Market Health:** 24h vol $2.1M | Overround 1.4% | 14 teams tracked
```

Rules:
- All matched teams shown in full table
- Sections omitted if no data (no games yesterday, no injuries)

---

## Architecture & Data Flow

```
state.json ──────────────────────────────┐
latest_signals.json (snapshot section) ──┤
                                          ▼
ESPN scoreboard API ──────────────────► daily_snapshot.py
ESPN injuries API ────────────────────►       │
                                              │
                      ┌───────────────────────┼──────────────────────┐
                      ▼                       ▼                      ▼
        snapshot_telegram.txt    snapshot_twitter.txt    snapshot_newsletter.txt
                      │                       │
                      ▼                       ▼
              telegram_bot.py           twitter_bot.py
              (called with flag)        (called with flag)
```

**Key constraints:**
- `daily_snapshot.py` is **read-only** on `state.json` and `latest_signals.json` — the signal engine owns those files
- `daily_snapshot.py` posts directly using the same Telegram Bot API and tweepy calls as the existing bots — no `--file` flag needed, posting logic is self-contained in the snapshot script
- ESPN fetches wrapped in try/except — failure degrades gracefully, never blocks the post

---

## GitHub Actions Schedule

New job added to `.github/workflows/scheduler.yml`:

```yaml
daily-snapshot:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/cache@v4
      with:
        path: |
          state.json
          latest_signals.json
        key: signal-state
    - run: pip install -r requirements.txt
    - run: python scripts/daily_snapshot.py
  schedule:
    - cron: '0 9 * * *'  # 9am UTC daily
```

The existing 4-hour signal engine job is untouched.

---

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| `latest_signals.json` missing | Exit with error — engine must run first |
| `state.json` missing | Post without overnight change column (show `—` for all) |
| ESPN scoreboard down | Post without scores section |
| ESPN injuries down | Post without injury section |
| Twitter post fails | Log error, do not retry, continue |
| Telegram post fails | Log error, do not retry, continue |

---

## Out of Scope

- Wallet/sharp-money signals (parked in `docs/sharp-money-signal.md`)
- Game-level (not championship) odds tracking
- Per-user threshold configuration
- Any write to `state.json` or `latest_signals.json`
