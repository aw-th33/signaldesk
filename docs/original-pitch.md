# F1 Prediction Market Intelligence Product — Evaluation Summary

## Context

We explored whether there is a viable business opportunity around Polymarket’s Builders Program by building an intelligence layer on top of prediction-market data.

The first broad idea was to build a prediction-market intelligence product rather than a generic trading bot, copy-trading tool, or Polymarket clone. The stronger direction was to create a trusted interpretation layer that turns prediction-market movement into useful insights.

We then narrowed the wedge to Formula 1.

The objective is **not** to build a venture-scale startup. The target is a **side, agentic-team-first business** capable of reaching roughly **$5K–$7K MRR**.

---

## Core Product Thesis

Build a specialist F1 probability intelligence product.

Working concept:

> Signal Desk: F1 probability intelligence for serious fans, bettors, fantasy players, and market watchers.

This should not start as a full SaaS dashboard or betting app. It should start as a **productized intelligence service** powered by agents.

The product should help users answer:

- What changed in the F1 market today?
- Which drivers, teams, or outcomes are being repriced?
- Which moves are meaningful versus low-liquidity noise?
- Why did a probability move happen?
- How do market probabilities compare with sportsbook odds, race data, news, weather, and expert consensus?
- What should serious F1 fans watch before qualifying or race day?

---

## Why F1 Is a Good Wedge

F1 has several useful characteristics:

- Passionate, data-interested fanbase
- Clear race-weekend rhythm
- Constant news flow
- Many uncertain outcomes
- Strong narratives around drivers, teams, upgrades, penalties, weather, qualifying, race strategy, and championship points
- Natural content cadence around each Grand Prix
- Enough niche intensity to support a small paid community

Potential market categories:

- Race winner
- Podium finish
- Qualifying winner
- Driver championship
- Constructor championship
- Safety car / red flag
- DNFs
- Team-mate battles
- Driver transfer rumors
- Regulation changes
- Penalties
- Weather-affected outcomes

---

## Contrarian View / Business Model Gaps

The idea has weaknesses that need to be tested.

### 1. F1 fans may not pay

F1 has a large audience, but much of the analysis ecosystem is free: YouTube, podcasts, Reddit, X/Twitter, fantasy communities, sports media, and betting sites.

The key question is:

> Is probability intelligence painful or valuable enough that serious fans will pay monthly?

### 2. Race calendar creates spikes, not daily utility

F1 creates strong demand on race weekends, but off-weeks may be quieter.

This creates potential churn unless the product covers:

- Championship probability
- Driver transfers
- Team upgrades
- Car development
- Weather
- Fantasy F1
- Market mispricing
- Off-season narratives

### 3. Polymarket liquidity may be shallow

Some markets may have enough volume to produce meaningful signals. Others may be thin and easily moved by small trades.

The product must distinguish between:

> Real market signal  
> vs  
> One trader moving a thin market

This requires liquidity filters and confidence scores.

### 4. Builder incentives may conflict with trust

Polymarket’s builder model may reward order flow and trading volume. A serious intelligence product should not push users into speculative trades just to monetize.

Trust is more important than volume.

### 5. Regulatory risk exists

Sports prediction markets can sit close to gambling / derivatives regulation depending on jurisdiction.

Initial positioning should be:

> Information, analytics, and market intelligence — not betting advice.

Avoid language like:

- Bet this
- Lock
- Guaranteed edge
- Free money
- Copy this trader
- Insider move

Use language like:

- Probability movement
- Market signal
- Confidence rating
- Watchlist
- Implied expectation
- Risk note

### 6. Basic dashboards are easy to copy

The defensibility cannot just be “we show Polymarket prices.”

The edge should come from:

- Market taxonomy
- Historical probability tracking
- Signal filtering
- AI explanations
- Race-weekend workflow
- Trusted editorial judgment
- Audience/community
- Good UX
- Multi-source data integration

---

## Business Model Target

The target is not venture-scale.

Goal:

> $5K–$7K MRR from a focused niche product.

Possible pricing paths:

| Price | Customers for $5K MRR | Customers for $7K MRR |
|---:|---:|---:|
| $10/mo | 500 | 700 |
| $19/mo | 264 | 369 |
| $29/mo | 173 | 242 |
| $49/mo | 103 | 143 |
| $99/mo | 51 | 71 |

Best likely pricing structure:

### Free Layer

Used for audience growth and trust-building.

Includes:

- Public race-weekend summaries
- Biggest F1 probability moves
- Market vs narrative posts
- Championship probability updates
- Newsletter snippets
- X/Twitter posts
- Reddit-safe discussion posts
- Simple public dashboard later

### Paid Layer — Pro

Potential price: **$19/month**

Includes:

- Race-weekend probability briefings
- Real-time Telegram/Discord alerts
- Biggest movers by 1h / 6h / 24h
- Market explanation summaries
- Driver/team watchlists
- Post-qualifying analysis
- Monday post-race probability debrief

### Paid Layer — Pro+

Potential price: **$49/month**

Includes:

- Everything in Pro
- Faster alerts
- Advanced charts
- Market vs sportsbook divergence
- Fantasy/betting angle notes
- More granular watchlists
- Private Telegram/Discord channel
- Race-weekend PDF reports

### Other Revenue Streams

Add later:

- Sponsorships
- One-off race reports
- Season preview reports
- Affiliate revenue
- Polymarket builder fees
- Data/API sales
- White-label intelligence widgets

---

## Recommended Product Positioning

Avoid:

> F1 betting dashboard

Better:

> The probability dashboard for serious F1 fans.

Or:

> Race-weekend intelligence for F1 bettors, fantasy players, and data-driven fans.

Or:

> F1 market intelligence powered by prediction markets, odds, news, and race data.

The product should feel like an intelligence desk, not a casino.

---

## MVP Strategy

Do not build a polished SaaS first.

Start with a manual / semi-automated intelligence product:

- Polymarket data ingestion
- Market tracking database
- Agent-generated summaries
- Human review/editorial judgment
- Newsletter
- Telegram or Discord alerts
- Simple landing page
- Optional public dashboard

The first goal is to validate attention and willingness to pay.

---

## Agentic Team Structure

The product can be run as a small virtual research desk.

### Agent 1: Market Monitor Agent

Responsibilities:

- Pull F1-related markets from Polymarket
- Track prices, probabilities, volume, liquidity, spreads, and open interest
- Detect 1h / 6h / 24h market movements
- Flag volume spikes
- Identify thin/noisy markets
- Classify signals by confidence

Outputs:

- Top movers
- Volume spike alerts
- Market signal confidence
- Noise warnings
- Watchlist updates

### Agent 2: F1 News & Context Agent

Responsibilities:

- Monitor official F1 sources, racing media, team announcements, driver quotes, penalties, weather, social chatter, and race control notes
- Summarize relevant developments
- Link news/context to market movements

Outputs:

- Likely reason for market move
- Source-backed explanations
- News relevance scoring
- Rumor vs official-source classification

### Agent 3: Race Weekend Analyst Agent

Responsibilities:

- Convert market and news data into usable insight
- Prepare race-weekend previews and recaps
- Interpret practice, qualifying, weather, penalties, upgrades, and race strategy implications

Outputs:

- Friday briefing
- Saturday qualifying preview
- Post-qualifying update
- Sunday race watch
- Monday post-race debrief

### Agent 4: Publishing Agent

Responsibilities:

- Turn intelligence into publishable content
- Create newsletters, Telegram alerts, X posts, Reddit-safe posts, and report sections

Outputs:

- Free posts
- Paid alerts
- Newsletter drafts
- Chart captions
- Community posts
- Weekly summaries

### Agent 5: Growth Agent

Responsibilities:

- Track content performance
- Suggest topics
- Identify F1 communities, subreddits, creators, and partnership opportunities
- Repurpose content into short-form posts

Outputs:

- Content calendar
- Growth experiments
- Community engagement ideas
- Post-performance analysis

---

## Core Data Requirements

### Polymarket Data

Need to ingest:

- Market ID
- Market title
- Outcomes
- Current prices / implied probabilities
- Volume
- Liquidity
- Open interest
- Spreads
- Historical price changes
- Timestamps
- Market status
- Event category / tags where available

### F1 Context Data

Potential sources:

- Official F1 schedule
- Race weekend sessions
- Practice results
- Qualifying results
- Race results
- Driver standings
- Constructor standings
- Team/driver announcements
- Weather
- Penalties
- Grid changes
- Tyre strategy
- Team upgrades
- Major racing publications
- Social sentiment, if available

### Optional Additional Data

- Sportsbook odds
- Fantasy F1 pricing
- Historical track data
- Driver/team historical performance
- Weather forecasts
- X/Twitter trend data
- Reddit discussion trends

---

## Product Features for MVP

### Must Have

- F1 market ingestion
- Market taxonomy
- Probability history tracking
- Biggest movers
- Volume/liquidity filters
- Confidence scoring
- Watchlists by driver/team/race
- Telegram or Discord alerts
- Newsletter generation
- Basic admin review workflow

### Nice to Have

- Public dashboard
- User accounts
- Custom alert thresholds
- Historical charts
- Market vs sportsbook divergence
- AI-generated “why did this move?” explanations
- Report export
- Polymarket builder integration

### Avoid Initially

- Full trading interface
- Copy trading
- Automated betting/trading bot
- Overbuilt SaaS dashboard
- Heavy regulatory exposure
- Complex mobile app

---

## Key Product Mechanic

The value is not showing a probability.

Weak output:

> Verstappen is 42% to win.

Strong output:

> Verstappen moved from 42% to 35% after FP2. The move appears meaningful because volume rose 3.8x and the spread tightened, rather than being caused by one thin trade. Likely drivers are McLaren’s long-run pace and Red Bull’s sector 2 weakness. Watch FP3 tyre degradation before treating this as confirmed.

The product must provide:

- What moved
- How much it moved
- Whether the move is credible
- Why it likely moved
- What to watch next
- What uncertainty remains

---

## Suggested Race-Weekend Content Cadence

| Day | Output |
|---|---|
| Monday | Post-race market debrief |
| Tuesday | Championship probability update |
| Wednesday | Upcoming race market preview |
| Thursday | Weather / upgrades / storyline watch |
| Friday | FP1 / FP2 probability movers |
| Saturday | Qualifying market update |
| Sunday | Race alerts + post-race recap |

---

## 30-Day Validation Plan

### Week 1: Set Up the Desk

- Pull Polymarket F1 markets into database
- Create market taxonomy
- Create landing page
- Create newsletter signup
- Create Telegram or Discord community
- Start posting public market-move content

### Week 2: Publish Free Race-Weekend Intelligence

- Friday preview
- FP1/FP2 movers
- Qualifying market update
- Race recap
- Championship probability update
- Track audience engagement

### Week 3: Launch Paid Beta

Offer:

> Founding member: $9/month for first 100 members.

Beta includes:

- Race-weekend alerts
- Private Telegram/Discord
- Weekly probability briefing
- Post-race debrief

### Week 4: Evaluate

Success indicators:

- 500+ email subscribers, or
- 50+ paid beta users, or
- strong engagement from serious F1/fantasy/betting users, or
- repeated inbound requests for alerts/data, or
- strong retention through multiple race weekends

Failure indicators:

- People like posts but do not subscribe
- Low engagement outside race weekends
- Polymarket F1 markets are too illiquid
- AI explanations are noisy or low-trust
- Content does not beat free F1 Twitter/Reddit analysis

---

## Technical Architecture — First Version

### Simple Stack

- Data ingestion worker
- Database
- Agent workflow
- Admin dashboard
- Newsletter publishing
- Telegram/Discord bot
- Basic landing page

### Possible Components

- Backend: Python or Node
- Database: Postgres / Supabase
- Scheduler: cron / GitHub Actions / Temporal / simple queue
- Frontend: Next.js
- Alerts: Telegram Bot API / Discord bot
- Newsletter: Beehiiv, Substack, ConvertKit, or Resend
- Agent framework: OpenClaw, LangGraph, CrewAI, or custom scripts
- Charts: Recharts / Plotly / simple image charts
- Hosting: Vercel + Supabase, or Railway/Fly.io

---

## Recommended Build Order

1. Market ingestion script
2. Market taxonomy/classification
3. Probability history database
4. Movement detection engine
5. Liquidity/confidence scoring
6. Admin review interface
7. Telegram/Discord alert bot
8. Newsletter generation workflow
9. Landing page
10. Public dashboard
11. Paid subscription integration
12. Polymarket builder integration, only later

---

## Confidence Scoring Logic

Each market move should have a confidence score.

Inputs:

- Absolute probability movement
- Percentage movement
- Volume increase
- Liquidity level
- Spread tightness
- Number of trades
- Time since last update
- Cross-source confirmation
- News match confidence
- Whether market is thin/noisy

Example labels:

- High confidence signal
- Medium confidence signal
- Low confidence / thin market
- News-driven move
- Rumor-driven move
- Unexplained move
- Likely noise

---

## Regulatory / Trust Guidelines

Position as analytics and intelligence.

Do not present as financial advice or betting advice.

Avoid:

- “Bet this”
- “Guaranteed”
- “Lock”
- “Free money”
- “Insider”
- “Copy this trader”
- “Sure win”

Use:

- “Market implies”
- “Probability moved”
- “Signal strength”
- “Watchlist”
- “Risk note”
- “Unconfirmed”
- “Low liquidity”
- “Confidence rating”

---

## Final Assessment

For a venture-scale company, F1 alone is probably too small.

For a side, agentic-team-first business targeting **$5K–$7K MRR**, this is a reasonable and testable opportunity.

The best version is:

> A small, premium, trusted F1 probability intelligence desk powered by agents.

The weakest version is:

> A generic F1 Polymarket dashboard.

The MVP should be content-led, alert-led, and trust-led before becoming software-led.

The most important validation questions:

1. Are there enough liquid F1 markets?
2. Do serious F1 fans care about probability movement?
3. Will users pay for faster/better interpretation?
4. Can agents produce useful summaries with human review?
5. Can the product become part of the race-weekend habit?
6. Can it avoid becoming a gambling-style product?
