# Signal Desk — Project Context

## What We're Building
A paid sports intelligence feed that monitors Polymarket sports prediction markets. It surfaces probability movements, sportsbook market divergences, and signal quality scores — delivered via Telegram.

## Business Target
$5K–$7K MRR side business. This is NOT venture-scale software. Minimal ops overhead. No dashboard, no auth, no mobile app for MVP.

## Tech Constraints
- Free-tier APIs only for validation (The Odds API 500 req/mo, Polymarket Gamma API public)
- No Betfair (geo-restricted, verification too burdensome)
- Delivery channel: Telegram bot → channel
- Hosting: GitHub Actions free tier OR $5/mo VPS (undecided)

## Key Strategic Decisions

### Wedge Sport: NBA (not F1)
- NBA: daily playoff games, massive bettor audience, $328M Polymarket volume
- F1: biweekly gaps kill content cadence; race-weekend markets are ghost towns ($0 vol, 0.90+ spreads)
- F1 championship-level tracking is viable but not the wedge

### 5 Signal Types for MVP
1. Divergence alerts (PM prob vs sportsbook implied prob)
2. Volume anomalies (e.g. Hornets $36.5M at 0.0% prob)
3. Overround spikes
4. Spread deterioration
5. Probability moves

### Delivery Strategy
1. **Free tier first (2 weeks)**: Post signals to X and Reddit to validate engagement
2. **Then paid**: Telegram bot posts alerts to a channel
3. **Pricing**: $9/mo founding member (50 cap), then $19/mo Pro, $49/mo Pro+

### Positioning
"Sports prediction market intelligence" — NOT "betting tips." Avoids regulatory heat.

## Key Data Points
- Polymarket sports futures volumes: FIFA WC $759M, NBA $328M, UCL $246M, F1 $127M, NHL $70M
- Polymarket overround: 0.4%–1.6% (near efficient) vs sportsbook overround: 12.9% (heavy margin)
- Long-shot volume anomaly exists across all sports (Hornets $36.5M at 0.0% prob)
- Boston Celtics showed -4.3pp divergence (PM 11.8% vs Books 16.1%) — proof the signal engine works
- No direct competitor exists at Polymarket × sports intelligence intersection

## What's Built

### Core Pipeline (MVP Complete)
- `scripts/signal_engine.py` — Combines PM + Odds API, detects 5 signal types (divergence, prob move, overround drift, spread deterioration, volume spike), diffs against `state.json`, outputs `latest_signals.json`
- `scripts/alert_formatter.py` — Reads signals, produces 3 format variants: Telegram (tagged one-liners), Twitter (compact top-2 under 280 chars), Newsletter (grouped with context)
- `scripts/telegram_bot.py` — Posts formatted alerts to Telegram channel via Bot API; skips when zero signals
- `scripts/twitter_bot.py` — Posts top-2 signals to X via tweepy; skips when zero signals
- `scripts/orchestrator.py` — Chains engine → formatter → Telegram → Twitter (~8s full pipeline)
- `requirements.txt` — requests, tweepy

### Infrastructure
- `.github/workflows/scheduler.yml` — GitHub Actions, runs every 4 hours (0 */4 * * *), state persists between runs via Actions cache (restore/save pattern)
- `state.json` — Persistent market state for diff detection, volume history for 7-day averages
- `latest_signals.json` — Machine-readable signal output consumed by formatters

### Delivery Channels (Live)
- **Telegram:** `@SignalDesk` channel, bot `@SignalDesk_Bot` posts when signals trigger
- **Twitter/X:** Automated posting via API v2 (credits purchased)
- **GitHub:** Repo at `github.com/aw-th33/signaldesk`, Actions scheduler active, secrets configured (ODDS_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL, TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET)

### Exploration Scripts
- `scripts/compare_nba.py` — NBA divergence + signal quality script
- `scripts/insights.py` — Cross-market overround, volume anomaly, synthetic odds
- `scripts/explore_polymarket.py` — Full tag/market/liquidity exploration
- `scripts/f1_deep_dive.py` — F1-specific market crawler
- `scripts/compare_pm_bf.py` — Betfair comparison (needs .env loading)

### Docs
- `docs/mvp-scope.md` — 4-component MVP build plan, signal thresholds, success metrics
- `docs/playbook.md` — 30-day execution plan (Phase 0–3)
- `docs/strategy.md` — Positioning, wedge choice, business model
- `docs/insights-and-opportunity.md` — Data findings, competitive gap, revenue math
- `docs/original-pitch.md` — Initial vision document

## What's NOT Built Yet (Phase 2)
1. **Landing page** — Carrd or static HTML on Vercel
2. **Paid tier** — Stripe payment link, private Telegram channel
3. **Historical dashboard** — 7-day/30-day probability trends
4. **Additional sports** — Soccer (UCL), NHL, F1 expansion
5. **Free content test** — Reddit posts to r/sportsbook, newsletter

## API Details
- The Odds API key: in `.env` as `ODDS_API_KEY`
- Sports key for NBA championship: `basketball_nba_championship_winner`
- Free tier: 500 req/month, 1 credit per query

## Competitive Landscape
- No direct competitor at Polymarket × sports intelligence intersection
- Comparable tools (not direct competitors): OddsJam $200/mo, Action Network $109/yr
- Polymarket dominates prediction market volume; no tool surfaces its sports data
