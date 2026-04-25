import requests, json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

GAMMA = "https://gamma-api.polymarket.com"

# F1-related tag IDs found in exploration
f1_tags = [
    (100389, "f1"),
    (100280, "formula-one"),
    (434, "racing"),
    (101411, "motorsports"),
    (102607, "f1-singapore-grand-prix"),
    (102654, "united-states-grand-prix"),
    (102029, "f2"),
    (100392, "redbull"),
    (100875, "verstappen"),
    (100877, "sainz"),
    (104133, "lance-stroll"),
    (104436, "qualifying"),
    (104383, "qualification"),
]

print("=" * 70)
print("F1 & MOTORSPORT MARKET DEEP DIVE")
print("=" * 70)

for tag_id, slug in f1_tags:
    try:
        resp = requests.get(f"{GAMMA}/tags/{tag_id}")
        if resp.status_code != 200:
            continue
        t = resp.json()
        label = t.get("label", "")
        print(f"\n--- Tag: {label} (id={tag_id}, slug={slug}) ---")
    except:
        continue

    # Get events
    try:
        events = requests.get(f"{GAMMA}/events", params={
            "tag_id": tag_id, "active": "true", "closed": "false", "limit": 20
        }).json()
        if not events:
            print("  No active events")
        for e in events:
            mkts = e.get("markets", [])
            print(f"  E: {e.get('title','')[:100]}")
            print(f"     vol24h=${e.get('volume24hr',0) or 0:,.0f}  "
                  f"total_vol=${e.get('volume',0) or 0:,.0f}  "
                  f"liq=${e.get('liquidity',0) or 0:,.0f}  "
                  f"mkts={len(mkts)}  slug={e.get('slug','')}")
            for m in mkts[:5]:
                q = (m.get("question") or "")[:100]
                vol = m.get("volumeNum") or 0
                liq = m.get("liquidityNum") or 0
                spread = m.get("spread")
                outcomes = m.get("outcomes")
                prices = m.get("outcomePrices")
                print(f"     M: {q}")
                print(f"        vol=${float(vol):,.0f}  liq=${float(liq):,.0f}  "
                      f"spread={spread}  outcomes={outcomes}  prices={prices}")
    except Exception as e:
        print(f"  Error: {e}")

# Also check closed markets for F1
print("\n" + "=" * 70)
print("FORMULA-ONE CLOSED MARKETS (for historical context)")
print("=" * 70)
try:
    closed = requests.get(f"{GAMMA}/markets", params={
        "tag_id": 100280, "closed": "true", "limit": 20, "order": "volume", "ascending": "false"
    }).json()
    print(f"Found {len(closed)} closed markets for formula-one tag:")
    for m in closed[:15]:
        q = (m.get("question") or "")[:120]
        vol = m.get("volumeNum") or 0
        liq = m.get("liquidityNum") or 0
        print(f"  {q}")
        print(f"    vol=${float(vol):,.0f}  liq=${float(liq):,.0f}  "
              f"spread={m.get('spread')}  outcomes={m.get('outcomes')}  prices={m.get('outcomePrices')}")
except Exception as e:
    print(f"  Error: {e}")

print("\nDONE")
