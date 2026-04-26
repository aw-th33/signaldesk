# Market Watchdog — Design Spec

**Date:** 2026-04-26
**Status:** Draft

## Summary

A standalone Telegram bot that lets active Polymarket traders monitor any market and receive personalized DMs when price, volume, or spread thresholds are breached. Separate from SignalDesk. New repo.

## Architecture

```
 Telegram Bot (webhook or long-poll)
      |
      ├── Config Mode: /watch, /unwatch, /threshold, /list, /pause, /help
      │     └── Writes ──▶ watchlist.json (per-user state)
      │
      └── Cron Mode (GitHub Actions, every 10 min):
            Market Poller ──▶ Gamma API ──▶ fetched prices/vol/spread
                                    │
                              Alert Evaluator ──▶ check per-user thresholds
                                    │
                              Alert Delivery ──▶ Telegram DM (if breached)
```

**No Odds API dependency.** 100% Polymarket Gamma API (free/public).

## Components

### 1. Config Handler (`config_handler.py`)
- Telegram commands: `/watch`, `/unwatch`, `/threshold`, `/list`, `/pause`, `/resume`, `/help`
- `/watch <query>` — resolves market via Gamma search endpoint, adds to user's watchlist with default thresholds
- `/threshold <market> <type> <value>` — sets custom threshold for a market
- Reads/writes `watchlist.json`

### 2. Market Poller (`market_poller.py`)
- Reads `watchlist.json`, collects all unique market slugs across all users
- Fetches current state for each slug from Gamma API: price (prob), volume, spread
- Passes data to Alert Evaluator

### 3. Alert Evaluator (`alert_evaluator.py`)
- For each user × market pair, checks if thresholds breached:
  - `prob_move`: abs(current_prob - last_prob) >= threshold
  - `vol_spike_ratio`: (24h_vol / running_avg_vol) >= threshold
  - `spread_above`: spread >= threshold
- Cooldown: skip if `last_alert_at` was within cooldown window (default 30 min)
- Returns list of (user_id, market_label, alert_message) tuples

### 4. Alert Delivery (`alert_delivery.py`)
- Sends DM via Telegram Bot API `sendMessage`
- HTML parse mode, no web preview
- Updates `last_alert_at` and `last_prob` in `watchlist.json`

### 5. State File (`watchlist.json`)

```json
{
  "users": {
    "123456789": {
      "alerts_paused": false,
      "markets": {
        "2026-nba-champion_oklahoma-city-thunder": {
          "label": "OKC Thunder",
          "slug": "2026-nba-champion",
          "token": "oklahoma-city-thunder",
          "thresholds": {
            "prob_move": 0.03,
            "vol_spike_ratio": 3.0,
            "spread_above": 0.01
          },
          "cooldown_min": 30,
          "last_prob": 0.525,
          "last_vol_24hr": 8818553.0,
          "last_spread": 0.01,
          "last_alert_at": null
        }
      }
    }
  }
}
```

Persistence across runs via GitHub Actions cache (restore → mutate → save), same pattern as SignalDesk `state.json`.

## API Usage

| Endpoint | Purpose | Rate |
|----------|---------|------|
| `gamma-api.polymarket.com/events/search?query=X` | Market lookup for `/watch` | On demand |
| `gamma-api.polymarket.com/events/slug/{slug}` | Get market data (prices, vol, spread) | Every 10 min per watched slug |
| `api.telegram.org/bot{token}/sendMessage` | Send DM alerts | Only when threshold breached |
| `api.telegram.org/bot{token}/getUpdates` | Receive commands (polling mode) | Every 3 sec (polling) or webhook |

**Zero API costs.** Gamma is free/public. Telegram Bot API is free. GitHub Actions free tier (2,000 min/mo) more than sufficient.

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/watch <query>` | Add a market. Bot resolves query via Gamma search. |
| `/unwatch <market>` | Remove a market from your watchlist. |
| `/list` | Show all watched markets with current thresholds and last values. |
| `/threshold <market> <type> <value>` | Set custom threshold. Types: `prob`, `vol`, `spread`, `cooldown`. |
| `/pause` | Pause all alerts. |
| `/resume` | Resume alerts. |
| `/help` | Show available commands. |

**Market resolution**: User types `/watch Lakers`. Bot queries Gamma search. If one match, adds immediately. If multiple matches, returns inline keyboard with up to 5 options for user to pick.

## Default Thresholds

| Type | Default | Description |
|------|---------|-------------|
| `prob_move` | 0.03 | Absolute probability change (3pp) since last alert |
| `vol_spike_ratio` | 3.0 | 24h volume / running 7-day average |
| `spread_above` | 0.01 | Alert when spread exceeds 1% |
| `cooldown_min` | 30 | Minutes before same market can re-alert |

## Alert Message Format

```
🔔 {label} ({event_title})
Prob ↑ +{change}pp ({old}% → {new}%)
Vol ${vol}K | Spread {spread}
```

Example:
```
🔔 OKC Thunder (NBA Champ)
Prob ↑ +4.2pp (48.5% → 52.7%)
Vol $82K | Spread 0.008
```

## Hosting & Scheduling

### Option A: VPS $5/mo (recommended for webhook)
- Telegram webhook for instant `/watch` responses
- Cron inside the process for market polling
- Lower latency, better UX

### Option B: GitHub Actions only (zero cost)
- Telegram long-polling for config commands (laggy but free)
- GitHub Actions cron for market polling every 10 min
- Slower `/watch` command resolution (poll-based, not instant)

### Decision: Start with Option B (GitHub Actions) for MVP validation. Upgrade to VPS if user experience suffers.

**Scheduler**: `.github/workflows/watchdog.yml` — runs every 10 minutes (`*/10 * * * *`). State restored/saved via Actions cache.

## Monetization

| Tier | Markets | Poll Interval | Custom Thresholds | Price |
|------|---------|---------------|--------------------|-------|
| Free | 3 | 30 min | No | $0 |
| Pro | 20 | 10 min | Yes | $5/mo |
| Pro+ | Unlimited | 5 min | Yes | $10/mo |

Implemented later via Stripe + feature flag checks in `watchlist.json` per-user `tier` field.

## MVP Scope (Phase 1)

1. Telegram bot with all config commands
2. Market polling via Gamma API
3. Three alert types (prob move, vol spike, spread above)
4. Per-user watchlists in `watchlist.json`
5. GitHub Actions cron every 10 min
6. Cooldown logic
7. No payments, no tier limits (free tier defaults for all)

## What's NOT in MVP

- Stripe/payments
- Webhook mode (polling only)
- Historical/trending view
- Dashboard or web UI
- SignalDesk integration/bundling
- Multiple Telegram channels (DM only)
- Batch summary digests (real-time only)

## Repo

New GitHub repo: `market-watchdog` (or similar). Separate from `signaldesk`. No code sharing, no dependency.

## Files

```
market-watchdog/
├── scripts/
│   ├── bot.py              # Telegram command handler
│   ├── market_poller.py    # Gamma API fetcher
│   ├── alert_evaluator.py  # Threshold checker
│   ├── alert_delivery.py   # Telegram DM sender
│   └── orchestrator.py     # Chains poll → eval → deliver
├── watchlist.json          # State file (Actions cache persisted)
├── requirements.txt
├── .env.example
├── .gitignore
└── .github/workflows/scheduler.yml
```
