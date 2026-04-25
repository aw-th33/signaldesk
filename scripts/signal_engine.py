import requests, json, os, sys, io, re, time
from datetime import datetime, timezone
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# --- CONFIG ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(BASE_DIR, "state.json")
SIGNALS_FILE = os.path.join(BASE_DIR, "latest_signals.json")
ODDS_API = "https://api.the-odds-api.com/v4"
PM_GAMMA = "https://gamma-api.polymarket.com"
ODDS_SPORT = "basketball_nba_championship_winner"
PM_SLUG = "2026-nba-champion"

# --- LOAD .ENV ---
env_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))

API_KEY = os.environ.get("ODDS_API_KEY", "") or (sys.argv[1] if len(sys.argv) > 1 else "")

# --- FETCH POLYMARKET ---
def fetch_polymarket():
    event = requests.get(f"{PM_GAMMA}/events/slug/{PM_SLUG}").json()
    markets = event.get("markets", [])

    data = {}
    for m in markets:
        q = (m.get("question") or "").replace("Will ", "").replace(" win the 2026 NBA Finals?", "")
        prices = json.loads(m.get("outcomePrices", "[]"))
        prob = float(prices[0]) if prices else 0
        vol_24hr = float(m.get("volume24hr", 0) or 0)
        data[q] = {
            "prob": prob,
            "vol": float(m.get("volumeNum", 0) or 0),
            "vol_24hr": vol_24hr,
            "liq": float(m.get("liquidityNum", 0) or 0),
            "spread": float(m.get("spread") or 0),
        }

    total_vol = float(event.get("volume", 0) or 0)
    total_vol_24hr = float(event.get("volume24hr", 0) or 0)
    return data, total_vol, total_vol_24hr


# --- FETCH ODDS API ---
def fetch_odds():
    resp = requests.get(f"{ODDS_API}/sports/{ODDS_SPORT}/odds", params={
        "apiKey": API_KEY, "regions": "us", "markets": "outrights", "oddsFormat": "decimal"
    })
    remaining = resp.headers.get("x-requests-remaining", "?")
    if resp.status_code != 200:
        print(f"Odds API error: {resp.text[:200]}")
        return {}, remaining

    sb_data = defaultdict(list)
    for entry in resp.json():
        for book in entry.get("bookmakers", []):
            for market in book.get("markets", []):
                for o in market.get("outcomes", []):
                    name = o.get("name", "")
                    price = o.get("price", 0)
                    if price and price > 1:
                        sb_data[name].append(1.0 / price)

    sb_avg = {}
    for team, implieds in sb_data.items():
        sb_avg[team] = sum(implieds) / len(implieds)

    return sb_avg, remaining


# --- NORMALIZE ---
def norm(name):
    name = re.sub(r"^(the|The)\s+", "", name)
    return re.sub(r"[^a-z]", "", name.lower())


# --- MATCH ---
def match(pm_data, sb_avg):
    pm_norm = {norm(k): k for k in pm_data}
    sb_norm = {norm(k): k for k in sb_avg}
    matched = {}
    for nk, sb_name in sb_norm.items():
        if nk in pm_norm:
            pm_name = pm_norm[nk]
            matched[sb_name] = {
                "pm_name": pm_name,
                "pm_prob": pm_data[pm_name]["prob"],
                "book_prob": sb_avg[sb_name],
                "vol": pm_data[pm_name]["vol"],
                "vol_24hr": pm_data[pm_name]["vol_24hr"],
                "liq": pm_data[pm_name]["liq"],
                "spread": pm_data[pm_name]["spread"],
                "gap": pm_data[pm_name]["prob"] - sb_avg[sb_name],
            }
    return matched


# --- STATE ---
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"markets": {}, "overround": None, "vol_history": {}, "signal_history": []}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, default=str)


# --- DETECTORS ---
def detect_divergence_change(matched, prev_markets, signals):
    for team, curr in matched.items():
        prev = prev_markets.get(team, {})
        prev_gap = prev.get("gap")
        if prev_gap is None:
            continue
        change = curr["gap"] - prev_gap
        if abs(change) >= 0.01:
            direction = "widening" if abs(curr["gap"]) > abs(prev_gap) else "narrowing"
            severity = "high" if abs(change) >= 0.03 else "medium"
            signals.append({
                "type": "divergence_change",
                "team": team,
                "severity": severity,
                "details": {
                    "pm_prob": round(curr["pm_prob"], 4),
                    "book_prob": round(curr["book_prob"], 4),
                    "current_gap": round(curr["gap"], 4),
                    "previous_gap": round(prev_gap, 4),
                    "change": round(change, 4),
                    "direction": direction,
                    "spread": curr["spread"],
                    "vol": curr["vol"],
                },
                "message": (
                    f"{direction[0].upper()}{direction[1:]} divergence: {team} "
                    f"PM {curr['pm_prob']:.1%} vs Books {curr['book_prob']:.1%} "
                    f"(gap {curr['gap']:+.1%}, changed {change:+.1%})"
                ),
            })


def detect_prob_moves(matched, prev_markets, signals):
    for team, curr in matched.items():
        prev = prev_markets.get(team, {})
        prev_prob = prev.get("pm_prob")
        if prev_prob is None:
            continue
        vol = curr.get("vol", 0)
        if vol < 100_000:
            continue
        change = curr["pm_prob"] - prev_prob
        if abs(change) >= 0.01:
            direction = "rising" if change > 0 else "falling"
            signals.append({
                "type": "probability_move",
                "team": team,
                "severity": "medium" if abs(change) < 0.03 else "high",
                "details": {
                    "pm_prob": round(curr["pm_prob"], 4),
                    "previous_prob": round(prev_prob, 4),
                    "change": round(change, 4),
                    "direction": direction,
                    "vol": curr["vol"],
                    "spread": curr["spread"],
                },
                "message": (
                    f"Probability {direction}: {team} "
                    f"{prev_prob:.1%} → {curr['pm_prob']:.1%} "
                    f"({change:+.1%}) on ${vol:,.0f} vol"
                ),
            })


def detect_overround_drift(matched, prev_overround, signals):
    probs = [m["pm_prob"] for m in matched.values() if m["pm_prob"] > 0]
    overround = sum(probs)
    if prev_overround is None:
        return overround
    drift = overround - prev_overround
    if abs(drift) >= 0.02:
        direction = "increasing" if drift > 0 else "decreasing"
        signals.append({
            "type": "overround_drift",
            "severity": "low" if abs(drift) < 0.04 else "medium",
            "details": {
                "current_overround": round(overround, 4),
                "previous_overround": round(prev_overround, 4),
                "drift": round(drift, 4),
                "direction": direction,
            },
            "message": (
                f"Overround {direction}: {prev_overround:.1%} → {overround:.1%} "
                f"(drift {drift:+.1%})"
            ),
        })
    return overround


def detect_spread_deterioration(matched, prev_markets, signals):
    for team, curr in matched.items():
        prev = prev_markets.get(team, {})
        prev_spread = prev.get("spread")
        if prev_spread is None:
            continue
        if prev_spread < 0.01 and curr["spread"] >= 0.01:
            signals.append({
                "type": "spread_deterioration",
                "team": team,
                "severity": "medium",
                "details": {
                    "pm_prob": round(curr["pm_prob"], 4),
                    "current_spread": curr["spread"],
                    "previous_spread": prev_spread,
                    "vol": curr["vol"],
                },
                "message": (
                    f"Spread deteriorated: {team} {prev_spread:.3f} → {curr['spread']:.3f} "
                    f"(prob {curr['pm_prob']:.1%})"
                ),
            })


def detect_volume_spike(matched, vol_history, signals):
    for team, curr in matched.items():
        v24 = curr.get("vol_24hr", 0)
        if v24 <= 0:
            continue
        history = vol_history.get(team, [])
        if len(history) >= 3:
            avg = sum(history) / len(history)
            if avg > 0 and v24 > 2 * avg:
                signals.append({
                    "type": "volume_spike",
                    "team": team,
                    "severity": "high" if v24 > 4 * avg else "medium",
                    "details": {
                        "pm_prob": round(curr["pm_prob"], 4),
                        "vol_24hr": v24,
                        "avg_vol_24hr": round(avg, 0),
                        "ratio": round(v24 / avg, 1) if avg > 0 else None,
                        "samples": len(history),
                    },
                    "message": (
                        f"Volume spike: {team} 24h ${v24:,.0f} "
                        f"vs {len(history)}-sample avg ${avg:,.0f} "
                        f"({v24/avg:.1f}x) — prob {curr['pm_prob']:.1%}"
                    ),
                })


# --- MAIN ---
def main():
    t0 = time.time()
    now = datetime.now(timezone.utc).isoformat()
    print(f"Signal Desk Engine — {now}")
    print("-" * 55)

    print("Fetching Polymarket data...")
    pm_data, pm_total_vol, pm_total_24hr = fetch_polymarket()
    print(f"  Markets: {len(pm_data)} | Total vol: ${pm_total_vol:,.0f} | 24h: ${pm_total_24hr:,.0f}")

    print("Fetching sportsbook odds...")
    sb_avg, remaining = fetch_odds()
    print(f"  Teams with odds: {len(sb_avg)} | API credits remaining: {remaining}")

    matched = match(pm_data, sb_avg)
    print(f"  Matched teams: {len(matched)}")

    print("Loading previous state...")
    state = load_state()
    prev_markets = state.get("markets", {})
    prev_overround = state.get("overround")
    vol_history = state.get("vol_history", {})

    signals = []

    print("Running detectors...")
    detect_divergence_change(matched, prev_markets, signals)
    detect_prob_moves(matched, prev_markets, signals)
    overround = detect_overround_drift(matched, prev_overround, signals)
    detect_spread_deterioration(matched, prev_markets, signals)
    detect_volume_spike(matched, vol_history, signals)

    print(f"  Signals detected: {len(signals)}")
    for s in signals:
        print(f"    [{s['severity'].upper():>6}] {s['type']}: {s.get('team', 'N/A')}")

    # Update vol_history with current 24h volumes
    new_vol_history = dict(vol_history)
    for team, curr in matched.items():
        v24 = curr.get("vol_24hr", 0)
        if v24 > 0:
            hist = new_vol_history.get(team, [])
            hist.append(v24)
            if len(hist) > 10:
                hist = hist[-10:]
            new_vol_history[team] = hist

    # Save new state
    new_markets = {}
    for team, curr in matched.items():
        new_markets[team] = {
            "pm_prob": curr["pm_prob"],
            "book_prob": curr["book_prob"],
            "gap": curr["gap"],
            "vol": curr["vol"],
            "vol_24hr": curr["vol_24hr"],
            "spread": curr["spread"],
            "liq": curr["liq"],
        }

    signal_history = state.get("signal_history", [])
    for s in signals:
        signal_history.append({"timestamp": now, **s})
    if len(signal_history) > 200:
        signal_history = signal_history[-200:]

    new_state = {
        "last_run": now,
        "markets": new_markets,
        "overround": overround,
        "vol_history": new_vol_history,
        "signal_history": signal_history,
    }
    save_state(new_state)
    print(f"State saved ({len(new_markets)} markets, {len(new_vol_history)} vol histories)")

    # Output signals file
    output = {
        "generated_at": now,
        "run_duration_sec": round(time.time() - t0, 2),
        "market": {
            "total_vol": pm_total_vol,
            "total_vol_24hr": pm_total_24hr,
            "overround": round(overround, 4),
            "matched_teams": len(matched),
        },
        "signals": signals,
        "snapshot": {
            team: {
                "pm_prob": curr["pm_prob"],
                "book_prob": curr["book_prob"],
                "gap": round(curr["gap"], 4),
                "vol": curr["vol"],
                "spread": curr["spread"],
            }
            for team, curr in sorted(matched.items(), key=lambda x: x[1]["pm_prob"], reverse=True)
        },
    }
    with open(SIGNALS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Signals written to {SIGNALS_FILE}")

    elapsed = time.time() - t0
    print(f"DONE in {elapsed:.1f}s with {len(signals)} signals")


if __name__ == "__main__":
    main()
