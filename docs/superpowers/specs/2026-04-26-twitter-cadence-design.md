# Twitter Cadence: 3-Hour Tweet Cycle

**Date:** 2026-04-26
**Status:** Approved
**Scope:** Increase Twitter posting frequency from opportunistic (0–7/day) to guaranteed 8/day via snapshot rotation.

---

## Motivation

Twitter algorithm requires posting volume to learn which audiences engage. Current setup tweets only when signals fire (ofte 0–2/day on quiet days) plus one daily snapshot. This is too sparse to build algorithmic reach.

## Goals

1. **Guaranteed tweet every 3 hours** — 8 tweets/day regardless of signal activity
2. **Variety** — Rotate across 8 data-driven snapshot types so followers see different angles
3. **No Odds API abuse** — Stay within free tier (500 req/mo). 8 runs × 30 days = 240 req/mo (48%).
4. **Telegram unchanged** — Telegram stays signal-only (no notification fatigue)
5. **Minimal new infrastructure** — Extend existing formatter, don't build a new pipeline

---

## Schedule Change

**scheduler.yml cron:** `0 */4 * * *` → `0 */3 * * *`

| UTC | ET (EDT) | Content |
|---|---|---|
| 00:00 | 8:00 PM | Twitter + Telegram |
| 03:00 | 11:00 PM | Twitter + Telegram |
| 06:00 | 2:00 AM | Twitter + Telegram |
| 09:00 | 5:00 AM | Twitter + Telegram + daily snapshot |
| 12:00 | 8:00 AM | Twitter + Telegram |
| 15:00 | 11:00 AM | Twitter + Telegram |
| 18:00 | 2:00 PM | Twitter + Telegram |
| 21:00 | 5:00 PM | Twitter + Telegram |

---

## Content Strategy

Each run, the Twitter formatter follows this decision tree:

```
signals exist?
├─ YES → tweet top 2 signals (existing behavior, unchanged)
└─ NO  → tweet next snapshot type from rotation (NEW)
```

### Signal path (unchanged)

Same as today: `fmt_twitter()` picks top 2 signals by severity, formats one-liners, appends "Full data in bio."

### Snapshot path (new)

8 template types, rotated round-robin. Rotation index persists in `state.json` under key `twitter_rotation_index`.

| Index | Type | Template |
|---|---|---|
| 0 | Leaderboard | `NBA Top 3: {t1} {p1}% (△) | {t2} {p2}% (△) | {t3} {p3}% (△)` |
| 1 | Divergence radar | `Biggest PM/Books gaps: {t1} {gap1}pp above | {t2} {gap2}pp below` |
| 2 | Volume watch | `Most 24h action: {t1} ${vol1}K | {t2} ${vol2}K | {t3} ${vol3}K` |
| 3 | Market pulse | `NBA champ market: Overround {ov}pp | 24h vol ${mv}M | {n} teams tracked` |
| 4 | Team spotlight | `{team}: PM {pm}% | Books {book}% | Gap {gap}pp | 24h vol ${vol}K` |
| 5 | Movers | `On the move: {t1} {chg1}pp ({prob}) | {t2} {chg2}pp ({prob})` |
| 6 | Sharp money | `High vol, low prob: {t1} ${vol1}K at {prob1}% | {t2} ${vol2}K at {prob2}%` |
| 7 | Gap story | `{team} {gap}pp gap: PM {pm}%, books {book}%. Info edge or market inefficiency?` |

All templates capped at ~200 chars to leave room for hashtags/link.

### Change arrows

For Leaderboard and Movers types, compare current PM prob against previous state (from `state.json` markets):
- `↑0.4pp` when change ≥ +0.3pp
- `↓0.4pp` when change ≤ −0.3pp
- `—` otherwise

### Data sources per type

| Type | Requires Odds API data? | Requires previous state? |
|---|---|---|
| Leaderboard (0) | No | Yes (for arrows) |
| Divergence radar (1) | Yes | No |
| Volume watch (2) | No | No |
| Market pulse (3) | No | No |
| Team spotlight (4) | Yes | No |
| Movers (5) | No | Yes (for deltas) |
| Sharp money (6) | No | No |
| Gap story (7) | Yes | No |

Types that require Odds API (1, 4, 7) degrade when book odds are unavailable (API failure or `snapshot` missing `book_prob`): skip to the next valid type, advancing rotation one step per skip. Sequence kept under 3 hops since at least 5 of 8 types are PM-only.

---

## Files Changed

### `scheduler.yml`
- Change cron `0 */4` → `0 */3`

### `alert_formatter.py`
- Add `fmt_twitter_snapshot(latest_signals, state_data)` function
  - Reads `twitter_rotation_index` from state (default 0)
  - Picks template, fills from `latest_signals.json` snapshot + `state.json` markets
  - Returns formatted tweet string
  - Increments and wraps index (0→1→...→7→0)
- Modify `main()`:
  - Load `state.json` at startup (in addition to `latest_signals.json` which it already loads)
  - When signals list is empty, call `fmt_twitter_snapshot()` instead of returning empty
  - Write output to `twitter.txt` regardless
  - After generating content, write the incremented `twitter_rotation_index` back to `state.json`
  - Orchestrator runs engine→formatter sequentially, so no race on state writes

### `twitter_bot.py`
- Remove early return when `latest_signals.json` has 0 signals
- Post `twitter.txt` if non-empty (always will be now)

### `signal_engine.py`
- Add `twitter_rotation_index: 0` to default state template (line 112)
- Persist it through state save/load (pass through unchanged)

### No changes to:
- `telegram_bot.py` — stays signal-only
- `daily_snapshot.py` — runs same time, same content
- `signal_engine.py` detectors — unchanged
- Landing page, RSS — unchanged
- `orchestrator.py` — unchanged

---

## State Schema Addition

`state.json` gains one top-level key:

```json
{
  "twitter_rotation_index": 2,
  ...existing keys...
}
```

Index increments from 0 to 7, wraps to 0. Non-critical — if missing, defaults to 0.

---

## Edge Cases

| Scenario | Behavior |
|---|---|
| No matched teams (PM + Odds mismatch) | Tweet: "NBA champ markets currently sparse. Standby." |
| Odds API returns empty (no book data) | Skip types 1, 4, 7; only rotate through PM-only types (0, 2, 3, 5, 6) |
| State file missing (first run) | Rotation starts at 0. Change arrows show "—" since no previous state. |
| Template exceeds 280 chars | Truncate to 274 chars + "…" |
| Manual workflow_dispatch | Works same as scheduled — rotation advances normally |
| Daily snapshot at 9am fires alongside | Two separate tweets: (1) snapshot tweet from formatter, (2) daily brief from `daily_snapshot.py`. Different content, both valid. |

---

## Odds API Budget

| Metric | Before | After |
|---|---|---|
| Runs/day | 6 | 8 |
| Odds API calls/day | 6 | 8 |
| Calls/month | ~180 | ~240 |
| % of 500 free tier | 36% | 48% |
| Headroom | 320 calls | 260 calls |

Still comfortable for adding a second sport later.

---

## Twitter API Budget

Two posting paths each run: `twitter_bot.py` (8x/day via orchestrator) + `daily_snapshot.py` (1x/day at 9am). Snapshot tweets replace signal tweets when no signals fire, so total per day stays at 8–9.

| Metric | Before | After |
|---|---|---|
| Tweets/day (max possible) | 7 | 9 |
| Tweets/day (typical) | 1–4 | **8–9** |
| Tweets/month | ~60–120 | **~270** |

### Per-tier utilization

| Tier | Monthly allotment | Utilization | Margin |
|---|---|---|---|
| **Free** | 500 posts/mo | 54% | Safe (230 posts headroom) |
| **Basic ($100/mo)** | 3,000 posts/mo | 9% | Massive headroom |

Free tier suffices. If the account is on Basic, the headroom is large enough to later add replies, quote-tweets, or image media without worry.

The `twitter_bot.py` and `daily_snapshot.py` each make 1 POST per tweet (tweepy `create_tweet` → `POST /2/tweets`), so each tweet = 1 API request.

### Rate limit guard

Twitter v2 POST rate limit is 200 requests per 15-minute window (app-level). At 1 tweet per run with 3h spacing, we're well under: 1 request per 180 minutes. Even daily snapshot + signal tweet at 9am same minute = 2 requests, far below 200.

---

## Success Metrics

- Twitter impressions/day should increase (more posting = more reach)
- Engagement rate should not drop significantly (content is data-rich, not spammy)
- No increase in unfollows (snapshot tweets are informational, not pushy)
- Telegram subscriber behavior unchanged (no notification spam)
