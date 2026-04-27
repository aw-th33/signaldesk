# Polymarket Links — Design Spec

## Summary
Add Polymarket market page links to every signal message, so subscribers can click through to trade.

## Source
Each market in the Gamma API response has a `slug` field already (e.g., `"will-the-oklahoma-city-thunder-win-the-2026-nba-finals"`).

## URL Format
`https://polymarket.com/event/2026-nba-champion/{slug}`

## Changes

### signal_engine.py
- `fetch_polymarket()`: add `"slug": m["slug"]` to pm_data dict
- `match()`: pass `slug` through to matched dict
- Signal details: include `slug` in every signal type's `details` dict

### alert_formatter.py
- Construct URL from signal `details.slug`
- Telegram: append raw URL after message (Telegram auto-linkifies)
- Twitter: append URL to tweet
- Newsletter: append URL after each signal

## Output Format
```
[DIVERGE] [MED] Oklahoma City Thunder PM 51.5% vs Books 54.6% (3.1% gap, books above PM)
https://polymarket.com/event/2026-nba-champion/will-the-oklahoma-city-thunder-win-the-2026-nba-finals
```
