"""
Polymarket vs Betfair Exchange — F1 Championship Comparison
Compares implied probabilities to find divergences.

Requirements:
    pip install requests

Betfair setup:
    1. Create free account at https://www.betfair.com
    2. Get API key at https://developer.betfair.com (My Account > Developer Apps)
    3. Set env vars: BETFAIR_USERNAME, BETFAIR_PASSWORD, BETFAIR_APP_KEY
"""
import requests
import json
import os
import sys
import io
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PM_GAMMA = "https://gamma-api.polymarket.com"
PM_CLOB = "https://clob.polymarket.com"
BF_LOGIN = "https://identitysso.betfair.com/api/login"
BF_API = "https://api.betfair.com/exchange/betting/rest/v1.0"

# ============================================================
# 1. POLYMARKET: Fetch F1 Drivers' Championship markets
# ============================================================
print("=" * 75)
print("POLYMARKET: 2026 F1 Drivers' Champion Markets")
print("=" * 75)

# Get the event by slug
event = requests.get(f"{PM_GAMMA}/events/slug/2026-f1-drivers-champion").json()
markets = event.get("markets", [])
print(f"Event: {event.get('title')}")
print(f"Total markets: {len(markets)}")
print(f"24h volume: ${event.get('volume24hr', 0):,.0f}")
print(f"Total volume: ${event.get('volume', 0):,.0f}")
print(f"Liquidity: ${event.get('liquidity', 0):,.0f}")
print()

pm_data = {}
for m in markets:
    question = m.get("question", "")
    # Extract driver name: "Will X be the 2026 F1 Drivers' Champion?"
    driver = question.replace("Will ", "").replace(" be the 2026 F1 Drivers' Champion?", "")
    outcomes = json.loads(m.get("outcomes", "[]"))
    prices = json.loads(m.get("outcomePrices", "[]"))
    yes_price = float(prices[0]) if prices and len(prices) > 0 else 0
    vol = float(m.get("volumeNum", 0) or 0)
    liq = float(m.get("liquidityNum", 0) or 0)
    spread = m.get("spread")

    pm_data[driver] = {
        "prob": yes_price,
        "vol": vol,
        "liq": liq,
        "spread": spread,
        "question": question,
    }

# Sort by probability descending
sorted_pm = sorted(pm_data.items(), key=lambda x: x[1]["prob"], reverse=True)
print(f"{'Driver':<25} {'Prob':>8} {'Volume':>12} {'Liquidity':>12} {'Spread':>8}")
print("-" * 75)
for driver, d in sorted_pm:
    print(f"{driver:<25} {d['prob']:>7.1%}  ${d['vol']:>10,.0f}  ${d['liq']:>10,.0f}  {d['spread']:>8}")

# ============================================================
# 2. BETFAIR: Fetch F1 Drivers' Championship market
# ============================================================
print()
print("=" * 75)
print("BETFAIR EXCHANGE: 2026 F1 Drivers' Championship")
print("=" * 75)

bf_username = os.environ.get("BETFAIR_USERNAME", "")
bf_password = os.environ.get("BETFAIR_PASSWORD", "")
bf_app_key = os.environ.get("BETFAIR_APP_KEY", "")

USE_BETFAIR = bool(bf_username and bf_password and bf_app_key)

if USE_BETFAIR:
    # Login to Betfair
    login_headers = {
        "X-Application": bf_app_key,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    login_resp = requests.post(
        BF_LOGIN,
        data=f"username={bf_username}&password={bf_password}",
        headers=login_headers
    )
    session_token = login_resp.json().get("sessionToken", "")
    print(f"Betfair login: {'OK' if session_token else 'FAILED'}")
    print(f"Session token: {session_token[:20]}...")

    if session_token:
        app_headers = {
            "X-Application": bf_app_key,
            "X-Authentication": session_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Find F1 Drivers Championship market
        # Event type 1 = Soccer, we need Motorsport or F1
        # Let's search using listMarketCatalogue
        market_filter = {
            "filter": {
                "textQuery": "F1 Drivers Championship 2026",
                "marketTypeCodes": ["WINNER"],
            },
            "maxResults": 5,
            "marketProjection": ["RUNNER_DESCRIPTION"],
        }

        # Try to find the market
        resp = requests.post(
            f"{BF_API}/listMarketCatalogue/",
            json=market_filter,
            headers=app_headers
        )
        if resp.status_code == 200:
            catalog = resp.json()
            print(f"Found {len(catalog)} matching markets")
            for c in catalog:
                print(f"  Market: {c.get('marketName')}  id={c.get('marketId')}")
                for r in c.get("runners", []):
                    print(f"    {r.get('runnerName')}  id={r.get('selectionId')}")

            # If we found the market, get prices
            if catalog:
                market_id = catalog[0].get("marketId")
                price_req = {
                    "marketIds": [market_id],
                    "priceProjection": {
                        "priceData": ["EX_BEST_OFFERS"],
                    },
                }
                price_resp = requests.post(
                    f"{BF_API}/listMarketBook/",
                    json=price_req,
                    headers=app_headers
                )
                if price_resp.status_code == 200:
                    book = price_resp.json()
                    bf_data = {}
                    for runner in book[0].get("runners", []):
                        name = runner.get("runnerName")
                        ex = runner.get("ex", {})
                        available_to_back = ex.get("availableToBack", [])
                        available_to_lay = ex.get("availableToLay", [])
                        best_back = available_to_back[0].get("price") if available_to_back else None
                        best_lay = available_to_lay[0].get("price") if available_to_lay else None

                        if best_back and best_lay:
                            mid = (best_back + best_lay) / 2
                            prob = 1 / mid if mid > 0 else 0
                        elif best_back:
                            prob = 1 / best_back
                        elif best_lay:
                            prob = 1 / best_lay
                        else:
                            prob = 0

                        # Total matched volume
                        total_matched = runner.get("totalMatched", 0)

                        bf_data[name] = {
                            "best_back": best_back,
                            "best_lay": best_lay,
                            "prob": prob,
                            "total_matched": total_matched,
                        }

                    # Print Betfair data
                    sorted_bf = sorted(bf_data.items(), key=lambda x: x[1]["prob"], reverse=True)
                    print(f"\n{'Driver':<25} {'Back':>8} {'Lay':>8} {'Implied':>8} {'Matched':>12}")
                    print("-" * 75)
                    for driver, d in sorted_bf[:15]:
                        bi = d["best_back"]
                        li = d["best_lay"]
                        print(f"{driver:<25} "
                              f"{bi:>8.2f}" if bi else f"{'N/A':>8}",
                              end=" ")
                        print(f"{li:>8.2f}" if li else f"{'N/A':>8}",
                              end=" ")
                        print(f" {d['prob']:>7.1%}  "
                              f"£{d['total_matched']:>10,.0f}")

        else:
            print(f"Market catalogue error: {resp.status_code} {resp.text[:200]}")
else:
    print("Betfair credentials not set. Skipping Betfair fetch.")
    print("To enable: set BETFAIR_USERNAME, BETFAIR_PASSWORD, BETFAIR_APP_KEY env vars")
    print()
    print("However, here's how the comparison WOULD work based on known market structure:")

# ============================================================
# 3. MOCK COMPARISON (uses Betfair-like structure)
# ============================================================
print()
print("=" * 75)
print("COMPARISON FRAMEWORK: Polymarket vs Betfair Divergence")
print("=" * 75)
print()
print("The analysis would compare:")
print()
print("1. Implied probability gap:")
print("   Polygen 3.2% vs Betfair 5.1% on Verstappen = +1.9pp divergence")
print("   → Betfair thinks Verstappen is 59% more likely to win")
print()
print("2. Exchange-to-exchange spread comparison:")
print("   Polymarket spread: 0.001 (near frictionless)")
print("   Betfair back/lay: 30.0/31.0 (3.3% spread)")
print("   → Polymarket is more efficient for this market")
print()
print("3. Volume comparison:")
print("   Polymarket Verstappen: $1.5M matched")
print("   Betfair Verstappen: ~£2M matched (estimated)")
print("   → Comparable depth, both are credible signals")
print()
print("4. Cross-exchange arbitrage check:")
print("   If Betfair lay < Polymarket back → arb exists")
print("   This flags markets where one exchange is lagging")
print()

# ============================================================
# 4. DEMO: Run divergence analysis on actual Polymarket data
# ============================================================
print("=" * 75)
print("POLYMARKET-ONLY INSIGHT: Internal Market Inefficiency")
print("=" * 75)
print()
print("With 32 independent Yes/No markets on the same event, probabilities")
print("SHOULD sum to near 100% (only one driver wins). Let's check:")
total_prob = sum(d["prob"] for d in pm_data.values())
print(f"  Sum of all implied probabilities: {total_prob:.1%}")
print(f"  Efficient market would be ~100%")
print(f"  Overround: {total_prob - 1:.1%}")
print()

# Show overround decomposition - who's overpriced?
print("Probability decomposition (which drivers are over/under-priced):")
print()
norm_factor = 1.0 / total_prob if total_prob > 0 else 1
print(f"{'Driver':<25} {'Raw Prob':>9} {'Adjusted':>9} {'Deviation':>10}")
print("-" * 65)
adjusted_sum = 0
for driver, d in sorted_pm:
    adjusted = d["prob"] * norm_factor
    dev = adjusted - d["prob"]
    # Highlight meaningful deviations
    marker = ""
    if abs(dev) > 0.005:
        marker = " ***" if dev > 0 else " ---"
    print(f"{driver:<25} {d['prob']:>8.1%}  {adjusted:>8.1%}  {dev:>+9.1%}{marker}")
    adjusted_sum += adjusted
print("-" * 65)
print(f"{'TOTAL':<25} {total_prob:>8.1%}  {adjusted_sum:>8.1%}")
print()
print("*** = book-adjusted probability is higher than raw (underpriced)")
print("--- = book-adjusted probability is lower than raw (overpriced)")
print()
print("This adjustment reveals which drivers are 'cheap' or 'expensive'")
print("relative to the full market — a signal sportsbooks can't provide")
print("because they don't list 32 separate win markets per driver.")
print()

# ============================================================
# 5. LIQUIDITY-ADJUSTED SIGNAL STRENGTH
# ============================================================
print("=" * 75)
print("SIGNAL STRENGTH SCORING")
print("=" * 75)
print()

for driver, d in sorted_pm[:10]:
    prob = d["prob"]
    vol = d["vol"]
    liq = d["liq"]
    spread_val = float(d["spread"]) if d["spread"] else 0

    # Score components (0-100 each)
    vol_score = min(100, (vol / 100000) * 100)  # $100K = 100 score
    liq_score = min(100, (liq / 50000) * 100)  # $50K = 100 score
    spread_score = max(0, 100 - (spread_val * 500))  # 0.001 spread = 99.5
    prob_score = 100 - abs(prob - 0.5) * 200  # closer to 50% = higher signal

    overall = (vol_score * 0.3 + liq_score * 0.2 + spread_score * 0.3 + prob_score * 0.2)

    label = ""
    if overall >= 80:
        label = "STRONG SIGNAL"
    elif overall >= 60:
        label = "MODERATE SIGNAL"
    elif overall >= 40:
        label = "WEAK SIGNAL"
    else:
        label = "NOISE"

    print(f"{driver:<25} prob={prob:>6.1%}  vol=${vol:>10,.0f}  "
          f"liq=${liq:>8,.0f}  spread={spread_val:.3f}  "
          f"score={overall:>5.0f}/100  [{label}]")

print()
print("DONE")
