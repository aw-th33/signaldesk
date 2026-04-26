# Landing Page Design Spec

**Date:** 2026-04-26
**Status:** Approved

## Overview

A single-page landing site for Signal Desk. One goal: funnel visitors into the free Telegram channel. No auth, no dashboard, no pricing — pure acquisition.

## Visual Direction

**Dark Terminal** — matching the existing Signal Desk banner aesthetic.

| Element | Value |
|---------|-------|
| Background | `#0B0B0C` base, subtle gradient to `#141414` |
| Text | White primary, grey `#999` secondary |
| Accent | Orange, used sparingly (CTAs, key numbers, icon highlights) |
| Cards | Semi-transparent dark (`rgba(255,255,255,0.03)`), thin `#222` border, soft shadow |
| Typography | Inter or Satoshi, bold geometric sans-serif. Headlines tight tracking, body comfortable line-height |
| Depth | Layering — background → faint gradient shapes → floating panels — creates "controlled complexity" |

## Sections

### 1. Hero

**Layout:** Left copy, right visual (matching banner composition).

- **Headline:** "Polymarket sports intel, delivered"
- **Subhead:** "NBA probability shifts, divergence alerts, and volume anomalies — sent to Telegram before the sportsbooks adjust."
- **CTA:** "Join Free on Telegram" button (orange accent, links to `t.me/SignalDesk`)
- **Visual:** 3 floating data panels with slight rotation and depth — Divergence, Volume Spike, Probability Shift — displaying real sample data

### 2. What We Track

5-card horizontal row, each: icon (orange accent glow) + signal name + one-liner.

1. **Divergence** — PM probability vs sportsbook implied probability gaps
2. **Volume Anomalies** — Unusual volume spikes on long-shot markets
3. **Overround Spikes** — Market inefficiency widening events
4. **Spread Deterioration** — Bid-ask spread widening signals
5. **Probability Moves** — Significant overnight probability shifts

Cards stack vertically on mobile.

### 3. Live Example

A realistic Telegram-style dark card showing a real signal (pulled from `latest_signals.json` at build time or hardcoded sample).

Format matches what users see in the Telegram channel — header, team data, and signal context.

### 4. Social Proof

3 stat cards in a row:
- **$X.XM** 24h volume tracked
- **X** teams monitored
- **X** signals sent

Stats pulled from live data if available, fallback to hardcoded examples.

### 5. CTA Footer

Repeat "Join Free on Telegram" button + `@SignalDesk` handle. Simple, no friction.

## Technical Decisions

**Platform:** Static HTML/CSS on Vercel. Single `index.html` with embedded CSS. Free hosting, auto-deploy from GitHub. Live stats injected at build time via a small Node.js script that reads `latest_signals.json` and replaces placeholders. Zero monthly cost.

## Out of Scope

- Pricing tiers (post-MVP)
- Auth / user accounts
- Blog / content pages
- Analytics beyond basic (no tracking pixels for MVP)
- Email capture (Telegram is the channel)
