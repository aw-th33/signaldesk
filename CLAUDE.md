# Apex Signal — Project Context

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
- `scripts/compare_nba.py` — NBA divergence + signal quality script (working, loads .env from root)
- `scripts/insights.py` — Cross-market overround, volume anomaly, synthetic odds
- `scripts/explore_polymarket.py` — Full tag/market/liquidity exploration
- `scripts/f1_deep_dive.py` — F1-specific market crawler
- `docs/mvp-scope.md` — 4-component MVP build plan, signal thresholds, success metrics
- `docs/playbook.md` — 30-day execution plan (Phase 0–3)
- `docs/strategy.md` — Positioning, wedge choice, business model
- `docs/insights-and-opportunity.md` — Data findings, competitive gap, revenue math
- `docs/original-pitch.md` — Initial vision document
- `.env` — Contains The Odds API key
- `opencode.json` — Superpowers plugin config

## What's NOT Built Yet (Next Steps)
1. **Signal engine** — combine compare_nba.py + insights.py + state tracking + diff detection
2. **Alert formatter** — JSON → Telegram/Twitter/newsletter text templates
3. **Telegram bot and channel** — BotFather setup, webhook or polling
4. **Landing page** — Carrd or static HTML on Vercel
5. **GitHub Actions scheduler** — `.github/workflows/scheduler.yml` (if Path A chosen)
6. **Free content test** — 2-week daily X posts + weekly newsletter to r/sportsbook
7. **compare_pm_bf.py** — needs .env loading added if Betfair path is revisited

## API Details
- The Odds API key: in `.env` as `ODDS_API_KEY`
- Sports key for NBA championship: `basketball_nba_championship_winner`
- Free tier: 500 req/month, 1 credit per query

## Competitive Landscape
- No direct competitor at Polymarket × sports intelligence intersection
- Comparable tools (not direct competitors): OddsJam $200/mo, Action Network $109/yr
- Polymarket dominates prediction market volume; no tool surfaces its sports data
