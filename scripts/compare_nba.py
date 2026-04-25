import requests, json, os, sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from collections import defaultdict

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))

ODDS_API = "https://api.the-odds-api.com/v4"
PM_GAMMA = "https://gamma-api.polymarket.com"
api_key = os.environ.get("ODDS_API_KEY", "") or (sys.argv[1] if len(sys.argv) > 1 else "")

# === POLYMARKET ===
event = requests.get(f"{PM_GAMMA}/events/slug/2026-nba-champion").json()
mkts = event.get("markets", [])

pm_data = {}
for m in mkts:
    q = (m.get("question") or "").replace("Will ", "").replace(" win the 2026 NBA Finals?", "")
    prices = json.loads(m.get("outcomePrices", "[]"))
    prob = float(prices[0]) if prices else 0
    pm_data[q] = {
        "prob": prob, "vol": float(m.get("volumeNum", 0) or 0),
        "liq": float(m.get("liquidityNum", 0) or 0),
        "spread": float(m.get("spread") or 0)
    }

# === THE ODDS API ===
resp = requests.get(f"{ODDS_API}/sports/basketball_nba_championship_winner/odds", params={
    "apiKey": api_key, "regions": "us", "markets": "outrights", "oddsFormat": "decimal"
})
remaining = resp.headers.get("x-requests-remaining", "?")
if resp.status_code != 200:
    print(f"Odds API error: {resp.text[:200]}"); sys.exit(1)

sb_data = defaultdict(list)
for entry in resp.json():
    for book in entry.get("bookmakers", []):
        bk = book.get("title", "?")
        for market in book.get("markets", []):
            for o in market.get("outcomes", []):
                name = o.get("name", "")
                price = o.get("price", 0)
                if price and price > 1:
                    sb_data[name].append({"bookmaker": bk, "price": price, "implied": 1.0 / price})

sb_avg = {}
for team, entries in sb_data.items():
    avg = sum(e["implied"] for e in entries) / len(entries)
    sb_avg[team] = {"avg_implied": avg, "sources": len(entries), "best_price": max(e["price"] for e in entries)}

# Normalize: strip "the", "The", lowercase, remove punctuation
def n(name):
    name = re.sub(r"^(the|The)\s+", "", name)
    return re.sub(r"[^a-z]", "", name.lower())
pm_norm = {n(k): (k, v) for k, v in pm_data.items()}
sb_norm = {n(k): (k, v) for k, v in sb_avg.items()}

# === HEADER ===
print("=" * 85)
print("POLYMARKET vs SPORTSBOOKS — NBA Champion Divergence Analysis")
print("=" * 85)
print(f"Polymarket: 24h Vol=${event.get('volume24hr',0):,.0f}  Total=${event.get('volume',0):,.0f}  Liq=${event.get('liquidity',0):,.0f}")
print(f"Sportsbooks: DraftKings, FanDuel, BetMGM, Caesars, Bovada (5 sources)")
print()

# === DIVERGENCE TABLE ===
print(f"{'Team':<25} {'PM Prob':>8} {'Book Avg':>9} {'Gap':>8}   {'Signal'}")
print("-" * 85)

big_gaps = []
for sb_name, sb in sorted(sb_avg.items(), key=lambda x: x[1]["avg_implied"], reverse=True):
    nn = n(sb_name)
    if nn in pm_norm:
        pm_name, pm = pm_norm[nn]
        gap = pm["prob"] - sb["avg_implied"]
        signal = ""
        if abs(gap) > 0.05:
            signal = "<<< CHEAP ON PM (big)" if gap < -0.05 else "EXPENSIVE ON PM (big) >>>"
            big_gaps.append((pm_name, pm, sb, gap))
        elif abs(gap) > 0.02:
            signal = "<< cheaper on PM" if gap < -0.02 else "pricier on PM >>"
        print(f"{pm_name:<25} {pm['prob']:>7.1%}  {sb['avg_implied']:>8.1%}  {gap:>+7.1%}   {signal}")

# === KEY INSIGHTS ===
print()
print("=" * 85)
print("KEY INSIGHTS")
print("=" * 85)
print()

if big_gaps:
    print("// Large divergence (>5pp) between Polymarket and sportsbooks:")
    for pm_name, pm, sb, gap in big_gaps:
        direction = "Polymarket MORE bearish — traders pricing lower than bookmakers" if gap < 0 else "Polymarket MORE bullish — traders pricing higher than bookmakers"
        print(f"  {pm_name}: PM {pm['prob']:.1%} vs Books {sb['avg_implied']:.1%} (gap {gap:+.1%}) — {direction}")
else:
    print("No extreme divergences (>5pp) found. Markets are well-aligned.")

print()
print(f"Tradeable markets found: {len(sb_norm)} teams matched across both platforms")
matched = [nn for nn in pm_norm if nn in sb_norm]
total_pm_prob = sum(pm_norm[nn][1]["prob"] for nn in matched)
total_sb_prob = sum(sb_norm[nn][1]["avg_implied"] for nn in matched)
print(f"PM sum of probabilities (matched teams): {total_pm_prob:.1%}")
print(f"Book sum of probabilities (matched teams): {total_sb_prob:.1%}")
print(f"Bookmaker overround: {total_sb_prob - 1:.1%} (normal — sportsbooks inflate for profit margin)")
print(f"PM overround: {total_pm_prob - 1:.1%} (near-zero = efficient market)")

# Missing
pm_only_teams = [(name, d) for n_name, (name, d) in pm_norm.items() if n_name not in sb_norm and d["prob"] > 0.005]
sb_only_teams = [(name, d) for n_name, (name, d) in sb_norm.items() if n_name not in pm_norm]
if pm_only_teams:
    print(f"\nPolymarket-only teams (not listed by sportsbooks):")
    for name, d in pm_only_teams:
        print(f"  {name}: {d['prob']:.1%}")
if sb_only_teams:
    print(f"\nSportsbook-only teams (not on Polymarket):")
    for name, d in sb_only_teams:
        print(f"  {name}: {d['avg_implied']:.1%}")

# === SIGNAL QUALITY ===
print()
print("=" * 85)
print("SIGNAL QUALITY SCORES")
print("=" * 85)
print(f"{'Team':<25} {'Prob':>7} {'Vol ($)':>10} {'Liq ($)':>10} {'Spread':>7} {'Score':>6}")
print("-" * 85)
for t, d in sorted(pm_data.items(), key=lambda x: x[1]["prob"], reverse=True):
    if d["prob"] <= 0: continue
    v_s = min(100, d["vol"]/500000*100)
    l_s = min(100, d["liq"]/100000*100)
    s_s = max(0, 100 - d["spread"]*1000)
    p_s = 100 - abs(d["prob"] - 0.5)*200
    score = v_s*0.3 + l_s*0.2 + s_s*0.3 + p_s*0.2
    bar = chr(9608)*int(score/5) + chr(9617)*(20-int(score/5))
    rating = "STRONG" if score>=70 else ("MODERATE" if score>=50 else ("WEAK" if score>=30 else "NOISE"))
    print(f"{t:<25} {d['prob']:>6.1%} {d['vol']:>9,.0f} {d['liq']:>9,.0f} {d['spread']:>6.3f} {score:>5.0f}  {bar}  {rating}")

print()
print(f"Credits used: {500 - int(remaining)}/500 this month")
print("DONE")
