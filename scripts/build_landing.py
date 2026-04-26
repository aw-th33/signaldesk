import json, os, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIGNALS_FILE = os.path.join(BASE_DIR, "latest_signals.json")
LANDING_FILE = os.path.join(BASE_DIR, "landing", "index.html")


def main():
    if not os.path.exists(SIGNALS_FILE):
        print("latest_signals.json not found. Skipping landing page build.")
        sys.exit(0)

    if not os.path.exists(LANDING_FILE):
        print("landing/index.html not found. Skipping.")
        sys.exit(1)

    with open(SIGNALS_FILE, encoding="utf-8") as f:
        signals = json.load(f)

    with open(LANDING_FILE, encoding="utf-8") as f:
        html = f.read()

    market = signals.get("market", {})
    snapshot = signals.get("snapshot", {})

    vol_24h = market.get("total_vol_24hr", 0)
    overround = market.get("overround", 1.0)
    teams_tracked = market.get("matched_teams", 0)

    vol_str = f"${vol_24h / 1_000_000:.1f}M"
    overround_pp = f"{(overround - 1.0) * 100:.1f}pp"

    example_team = "Celtics"
    example_pm_prob = 12.2
    example_book_prob = 16.3
    example_gap = -4.0
    example_vol = "$340K"
    example_hashtag = "Celtics"

    if snapshot:
        top_team = max(snapshot.items(), key=lambda x: x[1].get("pm_prob", 0))
        team_name, data = top_team
        example_team = team_name
        example_pm_prob = data.get("pm_prob", 0) * 100
        example_book_prob = data.get("book_prob", 0) * 100
        example_gap = data.get("gap", 0) * 100
        vol = data.get("vol", 0)
        if vol >= 1_000_000:
            example_vol = f"${vol / 1_000_000:.1f}M"
        else:
            example_vol = f"${vol / 1000:.0f}K"
        example_hashtag = team_name.split()[-1]

    replacements = {
        "{{VOL_24H}}": vol_str,
        "{{TEAMS_TRACKED}}": str(teams_tracked),
        "{{OVERROUND}}": overround_pp,
        "{{EXAMPLE_TEAM}}": example_team,
        "{{EXAMPLE_PM_PROB}}": f"{example_pm_prob:.1f}",
        "{{EXAMPLE_BOOK_PROB}}": f"{example_book_prob:.1f}",
        "{{EXAMPLE_GAP}}": f"{example_gap:+.1f}",
        "{{EXAMPLE_VOL}}": example_vol,
        "{{EXAMPLE_TEAM_HASHTAG}}": example_hashtag,
    }

    for placeholder, value in replacements.items():
        if placeholder in html:
            html = html.replace(placeholder, value)
        else:
            print(f"Warning: placeholder {placeholder} not found in HTML")

    with open(LANDING_FILE, encoding="utf-8") as f:
        current = f.read()

    if html == current:
        print("Landing page unchanged. No commit needed.")
        return

    with open(LANDING_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Landing page updated - {vol_str} volume, {teams_tracked} teams, {overround_pp} overround")
    print(f"Example: {example_team} {example_pm_prob:.1f}% PM vs {example_book_prob:.1f}% books ({example_gap:+.1f}pp)")


if __name__ == "__main__":
    main()
