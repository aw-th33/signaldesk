# Strategy

## What we're building

A paid intelligence service for sports bettors, fantasy players, and market watchers. Not a dashboard. Not a trading platform. A signal feed.

The product watches Polymarket's sports futures markets continuously and surfaces what matters: which odds moved, whether the move is credible, and why it probably happened. Delivered as a Telegram channel. Priced at $19/month.

## Positioning

Weak positioning: "F1 betting dashboard" or "Polymarket odds tracker."

Strong positioning: "The intelligence desk for sports prediction markets."

This matters because the first version says "betting tool" and attracts regulatory attention. The second says "market analysis" and attracts serious users. Same product. Different frame.

The product should read like a research desk, not a casino. Language matters: "probability movement" not "lock." "Confidence score" not "guaranteed edge." "Market signal" not "bet this."

## Why now

Three tailwinds:

1. Polymarket's sports volume is growing. The NBA championship market has $328M in matched volume. The FIFA World Cup has $759M. This didn't exist two years ago.

2. Prediction markets are crossing into mainstream awareness. Action Network added a prediction markets hub. Major sportsbooks are launching their own prediction products (FanDuel Predicts, DraftKings Predictions). The audience for prediction market content is bigger than ever.

3. No one has built tooling for this audience. The data exists. The API is public. The volume is real. But the interpretation layer — the thing that tells you which moves matter — doesn't exist.

## Market wedge: NBA

F1 was the original idea, but it has a structural problem. Races happen every two weeks. Championship odds don't move much between weekends. The content cadence gaps are too long for a daily alert product.

NBA solves this. Playoff games happen daily from April through June. Every game moves championship odds. Every injury shifts the probability landscape. There's always something to report.

The audience is also larger. NBA betting is a massive category. The NBA subreddit has 11M subscribers. r/sportsbook has 2M. The attention surface is orders of magnitude bigger than F1.

Start with NBA. Prove the model works. Soccer and F1 come next.

## Business model

Three tiers:

**Free** — Social posts on X and Reddit. Top 3 signals of the day. Newsletter snippet. Everything ends with "get this real-time: [link]." Purpose: audience building and trust.

**Pro ($19/month)** — Telegram channel. 5-8 alerts per day during the NBA playoffs. Divergence signals, volume anomalies, overround spikes, spread deterioration warnings. Faster than the free posts. Full field view included.

**Pro+ ($49/month)** — Everything in Pro plus custom watchlists (follow specific teams), historical charts, pre-game briefings, and access to a private Discord.

Additional revenue later: sponsorships, one-off reports, season preview PDFs, affiliate partnerships, Polymarket builder fees.

## The defensibility question

Showing Polymarket prices is not defensible. Anyone can do that.

The edge comes from:

- Signal filtering. Knowing which of 30 simultaneous price movements actually mean something.
- Confidence scoring. Every alert carries a quality grade. Users learn which signals they can trust.
- Speed. The bot fires before anyone has time to write a post about it.
- Accumulated trust. After 50 alerts that prove accurate, users stop questioning whether the next one matters.
- Multi-source integration. Comparing Polymarket to sportsbook odds, news events, and injury reports creates context that raw price data alone can't provide.

## What we're not building

- No trading interface. Users place their own bets wherever they want.
- No copy trading. We don't follow whales or recommend copying anyone.
- No mobile app. Telegram is the delivery channel. A landing page is the web presence.
- No betting advice. We report probability movement and confidence scores. We don't say "bet this."

## Revenue target

$5K-7K MRR. Not venture-scale. A side business run by a small team with agent assistance.

At $19/month, that's 264-369 subscribers. At a 2% conversion rate from free to paid, you need roughly 13,000-18,500 free subscribers. Achievable for a niche product over 6-12 months.

The goal is profit, not growth at all costs. Every subscriber after the first 50 is margin.
