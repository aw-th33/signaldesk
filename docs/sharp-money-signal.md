# Sharp Money Signal — Future Feature Note

**Status:** Parked for post-MVP. Validated by Reddit thread on r/sportsbook-style alert pain points.
**Date captured:** 2026-04-26

## Source
Reddit thread where Polymarket/Kalshi traders complained about alert systems. Key complaints:
- Existing Telegram bots are too noisy (80+ pings/day) or too slow (15-min polling)
- Users want wallet-level alerts, not just price-movement alerts
- Users want customizable thresholds ("only ping me for $50k+ moves")
- One commenter (polyman.fun) is already doing this for politics/crypto — **nobody is doing it for sports**

## The Insight
We currently tell users **that** a price moved or diverged. Wallet tracking tells them **who moved it** — and whether that "who" has been right before.

In sports specifically, large directional bets disproportionately come from people with an information edge (injury leaks, lineup news, sharp handicappers, syndicates). Sportsbooks have tracked "sharp action" for decades. Polymarket exposes equivalent data on-chain for free, and no one is surfacing it for sports.

## Three Layers of Value
1. **Confirmation** — user already had a thesis; sharp wallets confirm it → increases conviction
2. **Discovery** — surfaces plays the user wasn't watching
3. **Avoidance** — sharp wallets stacking the other side of a planned bet → saves losses (subscribers remember loss-avoidance more than wins)

## Positioning
Do **not** pitch as "wallet tracking" (sounds like a crypto tool). Pitch as **"sharp money alerts for prediction markets"** — sportsbook bettors already understand the concept.

Tagline candidates:
- *"Know when smart money moves — before the line does."*
- *"Sharp action tracking for Polymarket sports."*
- *"The bettors with the best track records just took a side. Here's where."*

## Pricing Leverage
Justifies the Pro tier jump:
- **$9 Founder** — current 5 signal types
- **$19 Pro** — adds sharp wallet alerts + per-user thresholds
- **$49 Pro+** — adds wallet-specific tracking ("ping me when wallet 0x... moves")

## Implementation Sketch (for later)
- Add as **6th signal type** in `scripts/signal_engine.py`, alongside divergence/volume/overround/spread/prob-move
- Data source: Polymarket on-chain trade data (subgraph or CLOB API), free
- Wallet quality score: win rate, ROI, market count, recency
- Conservative initial filter: **50+ resolved markets, 60%+ ROI** before a wallet counts as "sharp"
- Alert format: *"Sharp wallet entered [market] at [price], $X position. Wallet record: Y% across Z markets."*
- Use wallet quality as a **filter/amplifier on existing signals**, not a separate leaderboard product

## Honest Caveat
Wallet "skill" is noisy over short windows — a bad bettor can look sharp for 20 markets by variance alone. Start conservative on the threshold and label everything as "notable activity," not "winning bet," until we have confidence in the scoring.

## What to Ignore from the Thread
- **Sub-second websocket feeds** — irrelevant for our customer (1–3 plays/week, not HFT)
- **Copy trading** — different product, regulatory headache
- **Kalshi support** — wallets are private, kills the angle

## Competitor Note: Polycool (polycoolapp.com)
Mobile-first Polymarket app. Tracks top 0.5% of wallets, shows win rates (57.9%–73%) and PnL ($11K–$75K). Stack: smart feed, copy trading (up to 4 wallets, slippage guards), insider feed, custom Telegram alerts, auto-redeem. Free Telegram bot `@polycool_alerts` as the wedge, premium tier on top.

**Why we're not them:** Polycool is sport-agnostic — a $50k Trump bet and a $50k Lakers bet look identical in their feed. No injury context, no sportsbook line comparison, no overround analysis. An NBA-only bettor drowns in politics noise.

**Implication for us:** Don't position wallet tracking as a standalone feature — we'd be a tiny version of their product. Position it as an **amplifier on our existing sports signals**: "smart wallet entered + 4pp divergence vs DraftKings + overround spike" is a layered signal Polycool can't produce. They're horizontal; we're vertical.
