# Playbook

## Phase 0: foundation (this week)

**Set up the data pipeline**

We already have working scripts that pull data from Polymarket's Gamma API and The Odds API. The NBA comparison script produces divergence tables, signal quality scores, and volume anomaly detection. It runs in about 3 seconds and costs 1 API credit per run (500 free per month).

What needs to happen:
- Schedule it. Cron job or scheduled task. Every 4 hours during playoffs, every 12 hours during regular season.
- Store the output. Even just appending to a file. Historical tracking starts here.
- Add basic overround monitoring. Detect when the sum of probabilities crosses a threshold.
- Add spread deterioration detection. Flag markets where spread widens by 3x or more.

**Create the landing page**

One page. Carrd, Notion site, or a simple HTML file hosted on Vercel. Contents:
- What Signal Desk does (three bullet points)
- Sample alert (a screenshot or a formatted block showing what a subscriber sees)
- Newsletter signup (ConvertKit free tier or Substack)
- "Coming soon: Pro alerts" teaser

**Create social accounts**

- X/Twitter: @SignalDeskNBA (or similar)
- Reddit account
- Telegram channel (free tier, public)
- Discord server (optional, for community)

## Phase 1: free content (weeks 1-2)

Goal: validate that anyone cares. No paid product yet.

**Daily X posts**

Post the top 3 Polymarket NBA signals every day. Format:

```
NBA Championship Market Intel — April 25

Celtics NO divergence widens to -4.3pp
→ PM 11.8% | Books 16.1%
→ Books are 27% more bullish than the efficient market
→ Spread 0.001 | Vol $11.2M | Confidence: HIGH

Thunder YES holding at 52.5%
→ Stable since Tuesday despite no games
→ Liquidity strong at $301K

Hornets volume anomaly persists
→ $36.5M accumulated at 0.0% probability
→ No price movement. Short side defending.
```

End every post with a link to the newsletter or a "follow for more" call.

**Reddit posts in r/sportsbook**

Different format. The subreddit doesn't tolerate promotion. Lead with the insight, not the product.

```
I've been tracking Polymarket NBA championship odds 
vs sportsbook futures. Here's what I found this week:

[divergence table]

Key takeaway: Polymarket is systematically more 
bearish on favorites than sportsbooks. Boston is 
priced at 16.1% by books but 11.8% by the market.
Every other favorite shows the same pattern.

PM overround is 1.4%. Sportsbook overround is 12.9%.
If you're betting NBA futures at a sportsbook, you're
paying almost 10x the margin.

Full data and methodology in comments.
```

**Free newsletter**

One edition per week. Sunday evening. Content:
- Biggest probability moves of the week
- Market vs sportsbook divergence watchlist
- Overround health check
- One "signal of the week" explained in depth

Use Substack or ConvertKit. Free tier. Goal is email capture.

**Measure everything**

Track: impressions, replies, quote tweets, newsletter signups, Reddit upvotes/comments. If after two weeks the average post gets under 5 engagements, the idea might be wrong. If posts regularly get 10+ replies asking questions or requesting specific teams, you have signal.

## Phase 2: paid beta (weeks 3-4)

Trigger: at least one of these is true:
- 200+ newsletter subscribers
- Consistent 10+ engagement per Reddit post
- Direct messages asking "can I pay for this faster?"

**Launch the paid tier**

Pricing: $9/month founding member. Cap at 50 people. This isn't about revenue — it's about validation. If 50 people won't pay $9, you don't have a business.

Payment: Stripe payment link. No subscription management system yet. Manual onboarding.

**Deliverable: Telegram channel**

Private channel. Bot-powered. Format:

```
[Signal Desk Pro] Mon Apr 28 10:15 UTC

NBA CHAMPIONSHIP | Celtics NO @ 0.882
Divergence: -4.3pp (PM vs books)
Confidence: HIGH | Spread 0.001 | Vol $11.2M
Note: Gap widened 0.8pp since Friday. Market getting 
more bearish. No injury news driving this — possible 
smart money move. Watch for confirmation.

---
Overround alert: NBA futures drifted to 103.2% (was 101.4% 
on Thursday). Most of the drift is in the mid-tier teams. 
Lakers and Knicks lagging the repricing. Check those markets.

---
Volume watch: Hornets $36.5M → $38.1M. $1.6M added over 
weekend with no probability change. Someone is accumulating.
```

The bot runs on the same scripts. The difference from the free tier: faster (runs every 1-2 hours instead of daily), more signals (all detected divergences, not just the top 3), and includes the full field view.

**Gather feedback**

After two weeks of paid beta, ask every subscriber: what signal do you actually use? What would make you cancel? What would you pay more for? The answers shape what Pro+ looks like.

## Phase 3: iterate or pivot (week 5+)

**If retention is strong** (70%+ of beta users stay past week 2):
- Raise price to $19/month for new subscribers
- Add historical charts (7-day, 30-day probability trends)
- Expand to soccer (UCL winner market has $246M in volume)
- Build the Pro+ tier with custom watchlists and deeper analytics

**If retention is weak** (users sign up, try it, leave):
- The signals might be interesting but not actionable enough
- Try adding a "what to do with this" layer (not betting advice, but framing)
- Try a different sport (soccer, F1, NHL)
- Try a different format (daily email instead of Telegram, or vice versa)

**If nobody signs up at all:**
- The audience might not exist. That's the most important thing to learn.
- Before abandoning, try: different subreddits, different posting times, different formats, interview 5 people who engaged but didn't convert and ask why.

## Technical build order

These already exist from our exploration:
- Polymarket API connection and market parsing
- The Odds API integration for sportsbook comparison
- Divergence detection and signal scoring

What needs to be built:

1. **Scheduler** — Run scripts on a timer. Cron, GitHub Actions, or a simple while-true loop.
2. **State tracker** — Store previous run's data. Compare current to previous. Detect what changed.
3. **Alert formatter** — Turn raw JSON into the Telegram message format shown above.
4. **Telegram bot** — Connect to Telegram Bot API. Post to a private channel. Handle subscriptions.
5. **Landing page** — Carrd or simple HTML. Stripe link. Newsletter embed.
6. **Historical storage** — SQLite or a JSON file to start. Track probability over time.

## The first 24 hours

Day one checklist:

- [ ] Run NBA comparison script. Verify data is clean.
- [ ] Write 3 social posts from today's data. Post to X.
- [ ] Write 1 Reddit post. Post to r/sportsbook.
- [ ] Set up Carrd landing page with email signup.
- [ ] Create Telegram channel for future Pro tier.
- [ ] Schedule the script to run every 4 hours.

Total cost: $0. Total time: 4-6 hours. The scripts already work.
