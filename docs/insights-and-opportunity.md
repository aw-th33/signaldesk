# Insights and opportunity

## What we found in the data

Polymarket runs billions in sports futures volume with no sport-specific intelligence layer on top. We connected to their API and pulled data across four major sports. Here's what the numbers say.

### The volume is real

| Market | Total volume | 24h volume | Liquidity |
|--------|-------------|-----------|-----------|
| FIFA World Cup 2026 Winner | $759M | Active | $167M |
| NBA Champion | $328M | $4.5M | $9.7M |
| UEFA Champions League Winner | $246M | $632K | $1.97M |
| F1 Drivers' Champion | $127M | $1.3M | $12.1M |
| NHL Stanley Cup | $71M | $580K | $2.2M |

These are not niche markets. The FIFA World Cup winner market alone has $759M in matched volume. That's bigger than most sportsbooks' entire futures book.

### The markets are efficient

Polymarket's overround (the built-in margin) hovers between 0.4% and 1.6% across major sports futures. Traditional sportsbooks run at 12.9%. That means Polymarket prices reflect true probability far more accurately. For a bettor, this is the difference between paying a 13% tax on every bet versus paying almost nothing.

### The long-shot anomaly

The highest-volume trades don't go to favorites. Charlotte Hornets at 0.0% chance to win the NBA title has $36.5M in volume. Uzbekistan at 0.1% to win the World Cup has $33.4M. This pattern holds across every sport. It's speculators accumulating cheap long-shot tokens — a structural feature of prediction markets that sportsbooks don't expose.

### Race-specific F1 markets are empty

The championship futures have real liquidity. Per-race markets (Miami GP winner, pole position, fastest lap) are ghost towns. Most have $0 in volume and spreads over 0.90, meaning no real order book. A product built on race-weekend Polymarket data alone would starve. But the championship tracking is genuinely rich.

## What signals we can extract

We built scripts against the Polymarket API and The Odds API (free tier, 500 req/mo). Five distinct signals emerged, all automatable:

1. **Divergence alerts** — Polymarket probability vs sportsbook consensus. Boston Celtics: PM 11.8% vs books 16.1%. A 4.3pp gap. That's a 27% disagreement on their title odds. Which side is right? Either way, the gap itself is the signal.

2. **Volume anomalies** — When a 0.1% probability outcome has $10M in volume but the price isn't moving, something is happening. Someone is defending the short side. If volume spikes and probability ticks up simultaneously, consensus is breaking.

3. **Overround spikes** — Cross-market efficiency tracking. If F1 goes from 0.4% to 6% overround, it means some prices repriced while others went stale. That's an alert to go look at individual driver prices.

4. **Spread deterioration** — A previously tight market opening up (0.001 to 0.01+) means liquidity is pulling out. Something changed. Worth investigating.

5. **Synthetic fair odds** — Because Polymarket runs 30+ independent Yes/No markets per futures event, you can build a complete field probability table adjusted for spread risk. No sportsbook shows you this. It's unique to prediction market structure.

## The competitive gap

Nobody is doing this. Here's who comes closest:

- **PolymarketAnalytics.com** — Whale watching and trader leaderboards. General-purpose. No sport-specific filtering. No odds comparison.
- **OddsJam ($200/mo)** — Arbitrage across sportsbooks. No prediction market data.
- **Action Network ($109/yr)** — Editorial prediction market coverage. Not data-driven. No alerts. No F1.
- **F1FantasyTools** — Fantasy league optimizer. No betting. No prediction markets.
- **TheLines / Sportsbook Review** — Occasional articles about Polymarket. No tools, no subscription product.

The gap is specific: a paid intelligence feed that watches prediction market data for sports bettors and tells them what moved, whether it matters, and why. Nobody offers this for any sport. Not for NBA. Not for soccer. Not for F1.

## The revenue math

Target: $5K-7K MRR. This is a side business, not venture-scale.

At $19/month, you need 264-369 subscribers. At $49/month, 103-143.

The addressable audience isn't "all sports fans." It's people who already know what implied probability means. Sports bettors who understand the difference between a sportsbook line and a market price. Fantasy players who track win probabilities. The crossover of F1 fans, data-interested people, and prediction market users is small but intense. The NBA version of that audience is much bigger.

Start with NBA. Prove the model. Expand to soccer and F1 once the engine works.

## What we don't know yet

- Will people pay for probability movement alerts, or is this interesting-but-free territory?
- Can agent-generated summaries beat a sharp bettor's own reading of the market?
- How often do these signals produce actionable edges versus interesting-but-useless alerts?
- Does the audience churn between seasons, or is the futures market active enough year-round?

The only way to answer these is to run the free tier first and see who asks for more.
