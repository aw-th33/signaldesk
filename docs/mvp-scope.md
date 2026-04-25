# MVP scope

## What we're testing

One question: do people care? Everything else is distraction.

The MVP doesn't need to be good. It needs to exist. Three things to validate:

1. Can we produce a credible daily signal feed automatically?
2. Will anyone read it?
3. Will anyone ask for faster/more?

## What we build (4 components)

### 1. Signal engine

One Python script. Runs hourly. Takes the logic from `compare_nba.py` and `insights.py`, diffs against the previous run, and outputs a JSON file of what changed.

**Inputs:** Polymarket API + The Odds API
**Output:** `latest_signals.json` — a list of triggered signals with severity, confidence, and the raw comparison data

**Signals to detect:**
- Divergence change >1pp (PM vs books gap widened or narrowed)
- Probability movement >1pp on a >$100K volume market
- Overround drift >2%
- Spread deterioration (was <0.01, now >0.01)
- Volume spike (24h vol >2x 7-day average)

### 2. Alert formatter

Takes `latest_signals.json` and produces formatted text for humans. No AI generation. Template-based.

Three format variants:
- **Telegram alert** — 3-4 lines per signal. Succinct.
- **Twitter post** — 2-3 most interesting signals. Call to action at end.
- **Newsletter section** — Slightly longer. One sentence of context per signal.

### 3. Telegram bot

Public free channel. Posts 3-4 times per day during NBA playoffs.

Setup: create bot with @BotFather, invite to a channel, give it permission to post. The scheduler triggers the bot each cycle.

Free tier only at MVP stage. No paid channel. No subscriber gating.

### 4. Landing page

One page. Carrd is fine. Contains:
- Name: "Apex Signal"
- Subtitle: "NBA championship probability intelligence"
- 3 bullet points of what you get
- Email signup (ConvertKit or Substack embed)
- Links to Telegram and X

## What we skip

- No dashboard. Telegram is the UI.
- No user accounts. Email capture is the only identifier.
- No payment processing. That's Phase 2.
- No historical charts. That's Phase 2.
- No AI-generated explanations. Templates first. AI summaries later if the templates get traction.
- No custom watchlists. All teams, all signals.
- No mobile app. Telegram is already on every phone.

## Build order (one weekend)

**Day 1 (4 hours):**
1. Write the signal engine. Combine logic from compare_nba and insights into one script with state tracking.
2. Write the alert formatter. Three templates.
3. Test end-to-end: script runs, detects a signal, formats a message.

**Day 2 (3 hours):**
4. Set up Telegram bot and channel.
5. Wire scheduler to bot. Cron or GitHub Actions. Every 4 hours.
6. Build landing page. Carrd or one HTML file on Vercel.
7. Post the first alert. Share the link.

## State tracking (simplest possible)

One JSON file: `state.json`

```json
{
  "last_run": "2026-04-25T14:00:00Z",
  "markets": {
    "Oklahoma City Thunder": {"prob": 0.525, "book_prob": 0.554, "vol": 8715460},
    "Boston Celtics": {"prob": 0.118, "book_prob": 0.161, "vol": 11167800}
  },
  "overround": 1.015,
  "signal_history": [...]
}
```

On each run: load state, fetch fresh data, diff, write new state, emit signals.

## Signal detection thresholds (start here, tune later)

| Signal | Trigger |
|--------|---------|
| Divergence change | abs(pm_gap - prev_pm_gap) > 0.01 |
| Probability move | abs(prob - prev_prob) > 0.01 AND vol > 100000 |
| Overround drift | abs(overround - prev_overround) > 0.02 |
| Spread deterioration | spread > 0.01 AND prev_spread < 0.01 |
| Volume spike | vol24h > 2 * avg_vol24h_last_7d |

## Success metric

After two weeks:
- 50+ Telegram channel subscribers, OR
- 100+ newsletter signups, OR
- 5+ replies/DMs per day asking questions

Any one of these is enough to move to Phase 2. Zero is enough to kill it and try something else.
