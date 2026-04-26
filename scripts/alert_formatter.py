import json, os, sys, io
from datetime import datetime, timezone

_stdout_enc = getattr(sys.stdout, "encoding", "") or ""
if hasattr(sys.stdout, "buffer") and _stdout_enc.lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIGNALS_FILE = os.path.join(BASE_DIR, "latest_signals.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

STATE_FILE = os.path.join(BASE_DIR, "state.json")

TYPE_PREFIX = {
    "divergence_change": "[GAP]",
    "probability_move": "[MOVE]",
    "overround_drift": "[OVERROUND]",
    "spread_deterioration": "[SPREAD]",
    "volume_spike": "[VOLUME]",
}

SEVERITY_LABEL = {"high": "HIGH", "medium": "MED", "low": "LOW"}

SNAPSHOT_TYPES = [
    "leaderboard",
    "divergence_radar",
    "volume_watch",
    "market_pulse",
    "team_spotlight",
    "movers",
    "sharp_money",
    "gap_story",
]

ODDS_DEPENDENT_TYPES = {1, 4, 7}


def fmt_telegram(signals, meta):
    if not signals:
        return "[Signal Desk] " + meta["date"] + "\nNo triggered signals this cycle. Markets stable."

    lines = ["[Signal Desk] " + meta["date"]]
    lines.append("")

    for s in signals:
        tag = TYPE_PREFIX.get(s["type"], "[SIG]")
        sev = SEVERITY_LABEL.get(s["severity"], "LOW")
        lines.append(tag + " [" + sev + "] " + s["message"])
        lines.append("")

    return "\n".join(lines).strip()


def fmt_twitter(signals, meta):
    top = sorted(signals, key=lambda s:
        {"high": 3, "medium": 2, "low": 1}.get(s["severity"], 0), reverse=True)[:2]

    lines = ["NBA Market Intel -- " + meta["date"]]
    lines.append("")

    if not top:
        lines.append("Markets stable. No triggered signals.")
    else:
        for s in top:
            d = s.get("details", {})
            t = s["type"]
            team = s.get("team", "")
            line = ""

            if t == "divergence_change":
                chg = abs(round(d.get("change", 0) * 100, 1))
                line = "{} PM/Books gap {} {:.1f}pp (PM {:.0%} vs {:.0%})".format(
                    team, d.get("direction", "changed"), chg,
                    d.get("pm_prob", 0), d.get("book_prob", 0))
            elif t == "probability_move":
                chg = d.get("change", 0) * 100
                line = "{} prob {} {:.1%}->{:.1%} ({:+.1f}pp) ${:.0f}K vol".format(
                    team, d.get("direction", "moved"),
                    d.get("previous_prob", 0), d.get("pm_prob", 0),
                    chg, d.get("vol", 0) / 1000)
            elif t == "volume_spike":
                ratio = d.get("ratio", 1)
                line = "{} vol spike {:.0f}x avg (24h ${:.0f}K) prob {:.0%}".format(
                    team, ratio, d.get("vol_24hr", 0) / 1000, d.get("pm_prob", 0))
            elif t == "overround_drift":
                line = "Overround {} {:.1f}pp drift".format(
                    d.get("direction", "shifted"), abs(round(d.get("drift", 0), 3)))
            elif t == "spread_deterioration":
                line = "{} spread widened {:.3f}->{:.3f}".format(
                    team, d.get("previous_spread", 0), d.get("current_spread", 0))
            else:
                line = s.get("message", "")

            lines.append(line)
            lines.append("")

    lines.append("Full data in bio. Follow for more.")
    return "\n".join(lines).strip()


def fmt_newsletter(signals, meta):
    ov = meta.get("overround", 0)
    lines = ["NBA Championship Signals -- " + meta["date"]]
    lines.append("")
    overround_pct = (ov - 1.0) * 100
    lines.append("Overround: {:.1f}pp | Markets tracked: {}".format(
        overround_pct, meta.get("matched_teams", "?")))
    lines.append("")

    if not signals:
        lines.append("All markets within normal ranges. No signals triggered this cycle.")
        return "\n".join(lines)

    by_type = {}
    for s in signals:
        by_type.setdefault(s["type"], []).append(s)

    type_labels = {
        "divergence_change": "Divergence changes (PM vs sportsbooks)",
        "probability_move": "Probability moves",
        "overround_drift": "Overround drift",
        "spread_deterioration": "Spread deterioration",
        "volume_spike": "Volume spikes",
    }

    for stype, sigs in by_type.items():
        label = type_labels.get(stype, stype)
        lines.append("## " + label)
        for s in sigs:
            d = s.get("details", {})
            ctx = ""
            if stype == "divergence_change":
                ctx = "The gap between PM and sportsbooks is " + d.get("direction", "?") + "."
            elif stype == "probability_move":
                ctx = "Volume backing this move is ${:,.0f}.".format(d.get("vol", 0))
            elif stype == "volume_spike":
                ratio = d.get("ratio", "?")
                ctx = "24h volume is {}x the running average.".format(ratio)
            elif stype == "spread_deterioration":
                ctx = "Spread crossed the 0.01 threshold, liquidity may be thinning."
            elif stype == "overround_drift":
                ctx = "Direction: " + d.get("direction", "?") + "."

            lines.append("  [" + s["severity"].upper() + "] " + s["message"])
            if ctx:
                lines.append("    " + ctx)
        lines.append("")

    return "\n".join(lines).strip()


def _format_change_arrow(current_prob, prev_prob):
    if prev_prob is None:
        return "—"
    change_pp = (current_prob - prev_prob) * 100
    if change_pp >= 0.3:
        return f"↑{change_pp:.1f}pp"
    if change_pp <= -0.3:
        return f"↓{abs(change_pp):.1f}pp"
    return "—"


def _has_book_data(teams):
    for d in teams.values():
        bp = d.get("book_prob")
        if bp is not None and bp > 0:
            return True
    return False


def _pick_next_snapshot_type(current_index, teams=None):
    nxt = (current_index + 1) % 8
    chosen = nxt
    if teams is not None and not _has_book_data(teams):
        while chosen in ODDS_DEPENDENT_TYPES:
            chosen = (chosen + 1) % 8
    return nxt, chosen


def fmt_twitter_snapshot(data):
    teams = data.get("teams", {})
    market = data.get("market", {})
    prev_markets = data.get("prev_markets") or {}
    index = data.get("index", 0)

    if not teams:
        return "NBA champ markets currently sparse. Standby."

    sorted_by_pm = sorted(teams.items(), key=lambda x: x[1]["pm_prob"], reverse=True)

    # Type 0: Leaderboard
    if index == 0:
        top3 = sorted_by_pm[:3]
        parts = []
        for team, d in top3:
            pm_pct = d["pm_prob"] * 100
            prev = prev_markets.get(team, {}).get("pm_prob") if prev_markets else None
            arrow = _format_change_arrow(d["pm_prob"], prev)
            parts.append(f"{team} {pm_pct:.1f}% ({arrow})")
        out = "NBA Top 3: " + " | ".join(parts)
        return out if len(out) <= 280 else out[:274] + "…"

    # Type 1: Divergence radar
    if index == 1:
        sorted_by_gap = sorted(teams.items(), key=lambda x: x[1]["gap"], reverse=True)
        top = sorted_by_gap[0]
        bottom = sorted_by_gap[-1]
        t1, g1 = top[0], top[1]["gap"] * 100
        t2, g2 = bottom[0], bottom[1]["gap"] * 100
        return f"Biggest PM/Books gaps: {t1} {g1:+.1f}pp above | {t2} {g2:+.1f}pp below"

    # Type 2: Volume watch
    if index == 2:
        by_vol = sorted(teams.items(), key=lambda x: x[1]["vol"], reverse=True)[:3]
        parts = []
        for team, d in by_vol:
            vol_k = d["vol"] / 1000
            parts.append(f"{team} ${vol_k:.0f}K")
        return "Most 24h action: " + " | ".join(parts)

    # Type 3: Market pulse
    if index == 3:
        ov = (market.get("overround", 1.0) - 1.0) * 100
        total_24h = market.get("total_vol_24hr", 0)
        if total_24h >= 1_000_000:
            vol_str = f"${total_24h / 1_000_000:.1f}M"
        else:
            vol_str = f"${total_24h / 1000:.0f}K"
        n = market.get("matched_teams", len(teams))
        return f"NBA champ market: Overround {ov:.1f}pp | 24h vol {vol_str} | {n} teams tracked"

    # Type 4: Team spotlight
    if index == 4:
        top = sorted_by_pm[0]
        team, d = top[0], top[1]
        pm = d["pm_prob"] * 100
        book = d["book_prob"] * 100
        gap = d["gap"] * 100
        vol_k = d["vol"] / 1000
        return f"{team}: PM {pm:.1f}% | Books {book:.1f}% | Gap {gap:+.1f}pp | 24h vol ${vol_k:.0f}K"

    # Type 5: Movers
    if index == 5:
        changes = []
        for team, d in sorted_by_pm:
            prev = prev_markets.get(team, {}).get("pm_prob") if prev_markets else None
            if prev is None:
                continue
            chg_pp = (d["pm_prob"] - prev) * 100
            if abs(chg_pp) >= 0.3:
                changes.append((team, chg_pp, d["pm_prob"] * 100))
        if not changes:
            top2 = sorted_by_pm[:2]
            parts = [f"{t} {d['pm_prob']*100:.1f}% (—)" for t, d in top2]
            return "No significant moves. " + " | ".join(parts)
        top_movers = sorted(changes, key=lambda x: abs(x[1]), reverse=True)[:2]
        parts = [f"{t} {chg:+.1f}pp ({prob:.1f}%)" for t, chg, prob in top_movers]
        return "On the move: " + " | ".join(parts)

    # Type 6: Sharp money
    if index == 6:
        candidates = []
        for team, d in teams.items():
            vol = d["vol"]
            prob = d["pm_prob"]
            if vol >= 100_000 and prob <= 0.05:
                candidates.append((team, vol, prob))
        if not candidates:
            top = sorted_by_pm[0]
            team, d = top[0], top[1]
            vol_k = d["vol"] / 1000
            prob = d["pm_prob"] * 100
            return f"No speculative activity. Top vol: {team} ${vol_k:.0f}K at {prob:.1f}%"
        top2 = sorted(candidates, key=lambda x: x[1], reverse=True)[:2]
        parts = [f"{t} ${v/1000:.0f}K at {p*100:.1f}%" for t, v, p in top2]
        return "High vol, low prob: " + " | ".join(parts)

    # Type 7: Gap story
    if index == 7:
        sorted_by_abs_gap = sorted(teams.items(), key=lambda x: abs(x[1]["gap"]), reverse=True)
        top = sorted_by_abs_gap[0]
        team, d = top[0], top[1]
        pm = d["pm_prob"] * 100
        book = d["book_prob"] * 100
        gap = d["gap"] * 100
        direction = "PM above books" if gap > 0 else "books above PM"
        return f"{team} {abs(gap):.1f}pp gap: PM {pm:.1f}%, books {book:.1f}%. {direction} — info edge or noise?"

    return "NBA champ markets active. Full data in bio."


def main():
    if not os.path.exists(SIGNALS_FILE):
        print("No signals file found. Run signal_engine.py first.")
        sys.exit(1)

    with open(SIGNALS_FILE, encoding="utf-8") as f:
        data = json.load(f)

    # Load state.json for rotation index and previous markets
    state_data = {}
    twitter_rotation_index = 0
    prev_markets = None
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            state_data = json.load(f)
        twitter_rotation_index = state_data.get("twitter_rotation_index", 0)
        prev_markets = state_data.get("prev_markets")

    generated = data.get("generated_at", "")
    try:
        dt = datetime.fromisoformat(generated.replace("Z", "+00:00"))
        date_str = dt.strftime("%b %d %H:%M UTC")
    except Exception:
        date_str = generated

    meta = {
        "date": date_str,
        "overround": data.get("market", {}).get("overround", 0),
        "matched_teams": data.get("market", {}).get("matched_teams", 0),
    }
    signals = data.get("signals", [])
    snapshot = data.get("snapshot", {})
    market = data.get("market", {})

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    tg = fmt_telegram(signals, meta)

    # Twitter: signals if available, else snapshot rotation
    if signals:
        tw = fmt_twitter(signals, meta)
    else:
        next_idx, chosen_idx = _pick_next_snapshot_type(twitter_rotation_index, snapshot)
        tw = fmt_twitter_snapshot({
            "index": chosen_idx,
            "teams": snapshot,
            "market": market,
            "prev_markets": prev_markets,
        })
        twitter_rotation_index = next_idx

    nl = fmt_newsletter(signals, meta)

    for name, text in [("telegram", tg), ("twitter", tw), ("newsletter", nl)]:
        path = os.path.join(OUTPUT_DIR, name + ".txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print("=" * 60)
        print("[" + name.upper() + "]")
        print("=" * 60)
        print(text)
        print()

    # Save updated rotation index back to state
    if state_data is not None:
        state_data["twitter_rotation_index"] = twitter_rotation_index
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2, default=str)

    print("Written to output/telegram.txt, output/twitter.txt, output/newsletter.txt")


if __name__ == "__main__":
    main()
