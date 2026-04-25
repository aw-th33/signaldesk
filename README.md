# Apex Signal

F1 / NBA / Soccer prediction market intelligence. Tracks Polymarket futures markets and surfaces probability movements, sportsbook divergences, and signal quality scores.

## Folder structure

```
├── docs/          Strategy, playbook, research
├── scripts/       Data ingestion and analysis
├── output/        Script output (gitignored)
├── .env           API keys (gitignored)
└── .gitignore
```

## Quick start

1. Copy `.env` and add your keys
2. Run: `python scripts/compare_nba.py`

Get a free Odds API key at https://the-odds-api.com/#get-access

## Scripts

| Script | What it does |
|--------|-------------|
| `explore_polymarket.py` | Full Polymarket API exploration — tags, events, markets, liquidity, quality distribution |
| `f1_deep_dive.py` | F1-specific market deep dive — championship, race weekends, historical |
| `compare_nba.py` | Polymarket vs sportsbooks NBA championship comparison with divergence analysis |
| `compare_pm_bf.py` | Polymarket vs Betfair F1 comparison (requires Betfair credentials) |
| `insights.py` | Cross-market inefficiency, volume anomaly, and risk-adjusted probability analysis |
