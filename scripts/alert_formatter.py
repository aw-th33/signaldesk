import json, os, sys, io
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIGNALS_FILE = os.path.join(BASE_DIR, "latest_signals.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

TYPE_PREFIX = {
    "divergence_change": "[GAP]",
    "probability_move": "[MOVE]",
    "overround_drift": "[OVERROUND]",
    "spread_deterioration": "[SPREAD]",
    "volume_spike": "[VOLUME]",
}

SEVERITY_LABEL = {"high": "HIGH", "medium": "MED", "low": "LOW"}


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


def main():
    if not os.path.exists(SIGNALS_FILE):
        print("No signals file found. Run signal_engine.py first.")
        sys.exit(1)

    with open(SIGNALS_FILE, encoding="utf-8") as f:
        data = json.load(f)

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

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    tg = fmt_telegram(signals, meta)
    tw = fmt_twitter(signals, meta)
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

    print("Written to output/telegram.txt, output/twitter.txt, output/newsletter.txt")


if __name__ == "__main__":
    main()
