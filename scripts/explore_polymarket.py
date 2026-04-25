"""
Polymarket API Explorer — Tags, Markets, Liquidity Analysis
No auth required for Gamma & Data APIs.
"""
import requests
import json
import time
import sys
import io
from collections import defaultdict

# Fix Windows Unicode output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

GAMMA = "https://gamma-api.polymarket.com"
DATA = "https://data-api.polymarket.com"
CLOB = "https://clob.polymarket.com"

# ========================== 1. FETCH ALL TAGS ==========================
print("=" * 70)
print("1. ALL TAGS (categories on Polymarket)")
print("=" * 70)

tags = []
for offset in range(0, 1000, 100):
    resp = requests.get(f"{GAMMA}/tags", params={"limit": 100, "offset": offset})
    batch = resp.json()
    if not batch:
        break
    tags.extend(batch)
    if len(batch) < 100:
        break
    time.sleep(0.2)

print(f"Total tags: {len(tags)}")
for t in tags:
    print(f"  id={t.get('id'):>6}  slug={t.get('slug',''):<40} label={t.get('label','')}")
print()

# ========================== 2. SPORTS TAGS & METADATA ==========================
print("=" * 70)
print("2. SPORTS METADATA (and their tag IDs)")
print("=" * 70)

sports = requests.get(f"{GAMMA}/sports").json()
for s in sports:
    print(f"  sport={s.get('label',''):<25} tag_id={s.get('id','')}  "
          f"slug={s.get('slug','')}  active={s.get('active')}  "
          f"is_carousel={s.get('isCarousel')}")
print()

# ========================== 3. TOP EVENTS BY VOLUME ==========================
print("=" * 70)
print("3. TOP 30 ACTIVE EVENTS (by 24hr volume)")
print("=" * 70)

events = requests.get(f"{GAMMA}/events", params={
    "active": "true", "closed": "false",
    "order": "volume_24hr", "ascending": "false",
    "limit": 30
}).json()

for i, e in enumerate(events, 1):
    tags_str = ", ".join(t.get("label", "?") for t in (e.get("tags") or [])[:4])
    print(f"\n  {i:>2}. {e.get('title','')[:90]}")
    print(f"      24h vol=${e.get('volume24hr',0):,.0f}  "
          f"total vol=${e.get('volume',0):,.0f}  "
          f"liquidity=${e.get('liquidity',0):,.0f}  "
          f"OI=${e.get('openInterest',0):,.0f}  "
          f"markets={len(e.get('markets',[]))}")
    print(f"      tags: {tags_str}")
    print(f"      slug: {e.get('slug','')}")
    for m in (e.get("markets") or [])[:3]:
        print(f"        M: {m.get('question','')[:80]} "
              f"vol=${float(m.get('volumeNum',0) or 0):,.0f} "
              f"liq=${float(m.get('liquidityNum',0) or 0):,.0f} "
              f"spread={m.get('spread','?')}")
print()

# ========================== 4. TOP MARKETS BY VOLUME ==========================
print("=" * 70)
print("4. TOP 50 MARKETS (by total volume)")
print("=" * 70)

markets = requests.get(f"{GAMMA}/markets", params={
    "active": "true", "closed": "false",
    "order": "volume", "ascending": "false",
    "limit": 50
}).json()

for i, m in enumerate(markets, 1):
    tags_str = ", ".join(t.get("label", "?") for t in (m.get("tags") or [])[:3])
    vol = float(m.get("volumeNum", 0) or 0)
    liq = float(m.get("liquidityNum", 0) or 0)
    vol24 = m.get("volume24hr", 0) or 0
    spread = m.get("spread")
    print(f"  {i:>2}. {m.get('question','')[:90]}")
    print(f"      total_vol=${vol:,.0f}  24h_vol=${vol24:,.0f}  "
          f"liquidity=${liq:,.0f}  spread={spread}  "
          f"tags={tags_str}")
print()

# ========================== 5. LIQUIDITY DEEP DIVE ==========================
print("=" * 70)
print("5. LIQUIDITY ANALYSIS — markets sorted by liquidity, filtered by quality")
print("=" * 70)

markets_by_liq = sorted(markets, key=lambda m: float(m.get("liquidityNum", 0) or 0), reverse=True)

print("\nTop 20 by liquidity:")
for i, m in enumerate(markets_by_liq[:20], 1):
    vol = float(m.get("volumeNum", 0) or 0)
    liq = float(m.get("liquidityNum", 0) or 0)
    spread = m.get("spread")
    tags_str = ", ".join(t.get("label", "?") for t in (m.get("tags") or [])[:2])
    liq_vol_ratio = (liq / vol * 100) if vol > 0 else 0
    print(f"  {i:>2}. liq=${liq:,.0f}  vol=${vol:,.0f}  spread={spread}  "
          f"liq/vol={liq_vol_ratio:.1f}%  tags={tags_str}  "
          f"Q: {m.get('question','')[:70]}")

# ========================== 6. SPORTS-SPECIFIC DEEP DIVE ==========================
print()
print("=" * 70)
print("6. SPORTS-RELATED MARKETS (using sports tags)")
print("=" * 70)

for sport in sports[:15]:
    tag_id = sport.get("id")
    tag_label = sport.get("label", "")
    tag_slug = sport.get("slug", "")
    if not tag_id:
        continue

    try:
        sport_events = requests.get(f"{GAMMA}/events", params={
            "tag_id": tag_id, "active": "true", "closed": "false",
            "limit": 10
        }).json()
    except Exception:
        continue

    total_vol = sum(e.get("volume24hr", 0) or 0 for e in sport_events)
    total_mkts = sum(len(e.get("markets", [])) for e in sport_events)
    total_liq = sum(e.get("liquidity", 0) or 0 for e in sport_events)

    print(f"\n  --- {tag_label} (slug={tag_slug}, tag_id={tag_id}) ---")
    print(f"  Active events: {len(sport_events)}  "
          f"Markets: {total_mkts}  24h_vol=${total_vol:,.0f}  "
          f"Liquidity=${total_liq:,.0f}")

    for e in sport_events[:5]:
        vol24 = e.get("volume24hr", 0) or 0
        liq = e.get("liquidity", 0) or 0
        mkts = len(e.get("markets", []))
        print(f"    {e.get('title','')[:85]}")
        print(f"      24h_vol=${vol24:,.0f}  liq=${liq:,.0f}  mkts={mkts}  slug={e.get('slug','')}")
        for m in (e.get("markets") or [])[:2]:
            mvol = float(m.get("volumeNum", 0) or 0)
            mliq = float(m.get("liquidityNum", 0) or 0)
            spread = m.get("spread")
            print(f"        M: {m.get('question','')[:75]} vol=${mvol:,.0f} liq=${mliq:,.0f} spread={spread}")

    time.sleep(0.15)

# ========================== 7. F1 SPECIFIC CHECK ==========================
print()
print("=" * 70)
print("7. F1 / FORMULA 1 SPECIFIC SEARCH")
print("=" * 70)

# Try tag slugs
for slug in ["formula-1", "f1", "formula-one", "racing", "motorsport"]:
    try:
        resp = requests.get(f"{GAMMA}/tags/slug/{slug}")
        if resp.status_code == 200:
            tag = resp.json()
            print(f"  Found tag: {tag.get('label')}  id={tag.get('id')}  slug={tag.get('slug')}")
    except Exception:
        pass

# Try search
for query in ["formula 1", "F1", "formula one", "grand prix", "racing", "verstappen", "hamilton"]:
    try:
        resp = requests.get(f"{GAMMA}/search", params={"query": query, "limit": 5})
        if resp.status_code == 200:
            results = resp.json()
            mkts = [r for r in results if r.get("question")]
            events = [r for r in results if r.get("title") and not r.get("question")]
            if mkts or events:
                print(f"\n  Search '{query}': {len(events)} events, {len(mkts)} markets")
                for r in (mkts + events)[:5]:
                    if r.get("question"):
                        print(f"    M: {r.get('question','')[:90]}")
                    else:
                        print(f"    E: {r.get('title','')[:90]}  volume={r.get('volume','')}")
    except Exception:
        pass
    time.sleep(0.2)

# ========================== 8. MARKET QUALITY METRICS ==========================
print()
print("=" * 70)
print("8. MARKET QUALITY DISTRIBUTION (active markets)")
print("=" * 70)

vol_buckets = {"0": 0, "1-1K": 0, "1K-10K": 0, "10K-100K": 0, "100K-1M": 0, "1M+": 0}
liq_buckets = {"0": 0, "1-1K": 0, "1K-10K": 0, "10K-100K": 0, "100K-1M": 0, "1M+": 0}
spread_buckets = {"0": 0, "0.001-0.01": 0, "0.01-0.05": 0, "0.05-0.1": 0, "0.1-0.5": 0, "0.5+": 0}
vol_24h_buckets = {"0": 0, "1-100": 0, "100-1K": 0, "1K-10K": 0, "10K-100K": 0, "100K+": 0}

active_market_count = 0
for offset in range(0, 2000, 100):
    batch = requests.get(f"{GAMMA}/markets", params={
        "active": "true", "closed": "false",
        "limit": 100, "offset": offset
    }).json()
    if not batch:
        break
    active_market_count += len(batch)

    for m in batch:
        vol = float(m.get("volumeNum", 0) or 0)
        liq = float(m.get("liquidityNum", 0) or 0)
        spread = m.get("spread") or 0
        vol24 = m.get("volume24hr", 0) or 0

        for val, bucket in [(vol, vol_buckets), (liq, liq_buckets)]:
            if val == 0: bucket["0"] += 1
            elif val < 1000: bucket["1-1K"] += 1
            elif val < 10000: bucket["1K-10K"] += 1
            elif val < 100000: bucket["10K-100K"] += 1
            elif val < 1000000: bucket["100K-1M"] += 1
            else: bucket["1M+"] += 1

        spread = float(spread) if spread is not None else 0
        if spread == 0: spread_buckets["0"] += 1
        elif spread <= 0.01: spread_buckets["0.001-0.01"] += 1
        elif spread <= 0.05: spread_buckets["0.01-0.05"] += 1
        elif spread <= 0.1: spread_buckets["0.05-0.1"] += 1
        elif spread <= 0.5: spread_buckets["0.1-0.5"] += 1
        else: spread_buckets["0.5+"] += 1

        for val, bucket in [(vol24, vol_24h_buckets)]:
            if val == 0: bucket["0"] += 1
            elif val < 100: bucket["1-100"] += 1
            elif val < 1000: bucket["100-1K"] += 1
            elif val < 10000: bucket["1K-10K"] += 1
            elif val < 100000: bucket["10K-100K"] += 1
            else: bucket["100K+"] += 1

    time.sleep(0.15)
    if len(batch) < 100:
        break

print(f"Total active markets scanned: {active_market_count}")
print(f"\nVolume distribution:")
for k, v in vol_buckets.items():
    pct = v / active_market_count * 100 if active_market_count else 0
    print(f"  {k:>10}: {v:>5} ({pct:.1f}%)")

print(f"\n24h Volume distribution:")
for k, v in vol_24h_buckets.items():
    pct = v / active_market_count * 100 if active_market_count else 0
    print(f"  {k:>10}: {v:>5} ({pct:.1f}%)")

print(f"\nLiquidity distribution:")
for k, v in liq_buckets.items():
    pct = v / active_market_count * 100 if active_market_count else 0
    print(f"  {k:>10}: {v:>5} ({pct:.1f}%)")

print(f"\nSpread distribution:")
for k, v in spread_buckets.items():
    pct = v / active_market_count * 100 if active_market_count else 0
    print(f"  {k:>10}: {v:>5} ({pct:.1f}%)")

print()
print("=" * 70)
print("DONE — Exploration complete")
print("=" * 70)
