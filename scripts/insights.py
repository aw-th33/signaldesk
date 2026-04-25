import requests, json, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

GAMMA = "https://gamma-api.polymarket.com"
# F1 and NBA slugs
slugs = {
    "F1 Drivers Champion": "2026-f1-drivers-champion",
    "NHL Stanley Cup": "2026-nhl-stanley-cup-champion",
    "FIFA World Cup": "2026-fifa-world-cup-winner-595",
    "NBA Champion": "2026-nba-champion",
}

print("=" * 85)
print("CROSS-MARKET INEFFICIENCY ANALYSIS")
print("Each event has N independent YES/NO markets. All YES probs should sum to ~100%.")
print("Any deviation reveals inefficiency / opportunity.")
print("=" * 85)

for label, slug in slugs.items():
    e = requests.get(f"{GAMMA}/events/slug/{slug}").json()
    mkts = e.get("markets", [])
    yes_probs = []
    for m in mkts:
        prices = json.loads(m.get("outcomePrices", "[]"))
        p = float(prices[0]) if prices else 0
        if p > 0:
            yes_probs.append(p)

    total = sum(yes_probs)
    pmts = len(yes_probs)
    overround = total - 1.0
    fair_prob = 1.0 / pmts  # if perfectly uniform

    print(f"\n--- {label} ---")
    print(f"  Markets with YES>0: {pmts}")
    print(f"  Sum of probabilities: {total:.1%}")
    print(f"  Overround (excess above 100%): {overround:+.1%}")
    print(f"  Avg probability per outcome: {total/pmts:.1%}")
    print(f"  Top 3 account for {sum(sorted(yes_probs,reverse=True)[:3]):.1%} of probability")
    print(f"  Long-tail (bottom 20) account for {sum(sorted(yes_probs)[:20]):.1%}")
    print(f"  Smoothness: {max(yes_probs)/min(yes_probs):,.0f}x between max and min")

print()
print("=" * 85)
print("VOLUME ANOMALY ANALYSIS")
print("Where is money flowing that PROBABILITY doesn't predict?")
print("=" * 85)

for label, slug in slugs.items():
    e = requests.get(f"{GAMMA}/events/slug/{slug}").json()
    mkts = e.get("markets", [])
    data = []
    for m in mkts:
        q = (m.get("question") or "")[:50]
        prices = json.loads(m.get("outcomePrices", "[]"))
        prob = float(prices[0]) if prices else 0
        vol = float(m.get("volumeNum", 0) or 0)
        if vol > 0:
            data.append((q, prob, vol))

    if not data:
        continue

    total_vol = sum(d[2] for d in data)
    print(f"\n--- {label} (total vol: ${total_vol:,.0f}) ---")

    # Sort by volume, show top 5 by volume AND their probability
    by_vol = sorted(data, key=lambda x: x[2], reverse=True)[:5]
    print(f"  Top 5 by volume:")
    for q, prob, vol in by_vol:
        vol_pct = vol / total_vol * 100
        print(f"    {prob:>6.1%} prob  ${vol:>10,.0f} vol ({vol_pct:.0f}%)  -- {q}")

    # Correlation: which teams have disproportionately high volume vs probability?
    print(f"  Highest vol:prob ratio (most traded relative to odds):")
    ratios = [(q, prob, vol, vol/max(0.001,prob)) for q, prob, vol in data]
    for q, prob, vol, ratio in sorted(ratios, key=lambda x: x[3], reverse=True)[:5]:
        print(f"    {prob:>6.1%} prob  ${vol:>8,.0f} vol  ratio {ratio:,.0f}x  -- {q}")

print()
print("=" * 85)
print("RISK-ADJUSTED PROBABILITY DECOMPOSITION")
print("Sportsbooks quote one line per bet. Polymarket lets us see the ENTIRE field.")
print("=" * 85)

# Pick NBA since it has exact team names
e = requests.get(f"{GAMMA}/events/slug/2026-nba-champion").json()
mkts = e.get("markets", [])
nba_data = []
for m in mkts:
    q = (m.get("question") or "").replace("Will ", "").replace(" win the 2026 NBA Finals?", "")
    prices = json.loads(m.get("outcomePrices", "[]"))
    prob = float(prices[0]) if prices else 0
    vol = float(m.get("volumeNum", 0) or 0)
    liq = float(m.get("liquidityNum", 0) or 0)
    spread = float(m.get("spread") or 0)
    nba_data.append({"team": q, "prob": prob, "vol": vol, "liq": liq, "spread": spread})

total_prob = sum(d["prob"] for d in nba_data)
print(f"\nNBA Champion: 30 teams, total raw probability: {total_prob:.1%}")
print()

# Adjust for overround (normalize to 100%)
norm = 1.0 / total_prob
for d in nba_data:
    d["fair"] = d["prob"] * norm
    d["risk_adj"] = d["fair"] / (1.0 + d["spread"])  # penalize wide spreads

nba_sorted = sorted(nba_data, key=lambda x: x["prob"], reverse=True)
print(f"{'Team':<25} {'Raw':>7} {'Fair':>7} {'Risk-Adj':>9} {'Spread':>7} {'Confidence'}")
print("-" * 75)
for d in nba_sorted[:12]:
    conf = "HIGH" if d["spread"] < 0.005 and d["vol"] > 5e6 else "MED" if d["spread"] < 0.02 else "LOW"
    print(f"{d['team']:<25} {d['prob']:>6.1%} {d['fair']:>6.1%} {d['risk_adj']:>8.1%}  {d['spread']:>6.3f}  {conf}")

print()
print("This produces a 'synthetic odds table' that no single sportsbook shows —")
print("the full field, adjusted for market efficiency and execution risk.")
print()

print("=" * 85)
print("DONE — 3 additional insight layers demonstrated from Polymarket data alone")
print("=" * 85)
