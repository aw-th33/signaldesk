import json, os, sys, requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIGNALS_FILE = os.path.join(BASE_DIR, "latest_signals.json")
STATE_FILE = os.path.join(BASE_DIR, "state.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")



def load_snapshot_data(path=None):
    path = path or SIGNALS_FILE
    if not os.path.exists(path):
        print("latest_signals.json not found. Run signal_engine.py first.")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return {
        "generated_at": raw.get("generated_at", ""),
        "market": raw.get("market", {}),
        "teams": raw.get("snapshot", {}),
    }


def load_prev_state(path=None):
    path = path or STATE_FILE
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        state = json.load(f)
    return {
        team: data["pm_prob"]
        for team, data in state.get("markets", {}).items()
        if "pm_prob" in data
    }


ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
ESPN_INJURIES = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries"


def fetch_espn_scores():
    try:
        resp = requests.get(ESPN_SCOREBOARD, timeout=10)
        if resp.status_code != 200:
            return []
        games = []
        for event in resp.json().get("events", []):
            for comp in event.get("competitions", []):
                if not comp.get("status", {}).get("type", {}).get("completed"):
                    continue
                competitors = comp.get("competitors", [])
                if len(competitors) < 2:
                    continue
                by_side = {c["homeAway"]: c for c in competitors}
                home = by_side.get("home", {})
                away = by_side.get("away", {})
                home_score = int(home.get("score", 0) or 0)
                away_score = int(away.get("score", 0) or 0)
                home_name = home.get("team", {}).get("shortDisplayName", "")
                away_name = away.get("team", {}).get("shortDisplayName", "")
                if home_score == away_score:
                    continue
                if home_score > away_score:
                    winner, w_score, loser, l_score = home_name, home_score, away_name, away_score
                else:
                    winner, w_score, loser, l_score = away_name, away_score, home_name, home_score
                games.append({"winner": winner, "winner_score": w_score, "loser": loser, "loser_score": l_score})
        return games
    except Exception as e:
        print(f"ESPN scores fetch failed: {e}")
        return []


def fetch_espn_injuries():
    try:
        resp = requests.get(ESPN_INJURIES, timeout=10)
        if resp.status_code != 200:
            return []
        injuries = []
        for team_block in resp.json().get("injuries", []):
            team_name = team_block.get("team", {}).get("shortDisplayName", "")
            for inj in team_block.get("injuries", []):
                status = inj.get("status", "")
                # Only surface high-impact statuses; "Day-To-Day" and "Probable" intentionally excluded
                if status not in ("Out", "Questionable", "Doubtful"):
                    continue
                location = inj.get("details", {}).get("location", "")
                injuries.append({
                    "player": inj.get("athlete", {}).get("displayName", ""),
                    "team": team_name,
                    "status": status,
                    "location": location,
                })
        return injuries
    except Exception as e:
        print(f"ESPN injuries fetch failed: {e}")
        return []


def _overnight_arrow(change_pp):
    if change_pp >= 0.3:
        return f"📈 +{change_pp:.1f}pp"
    if change_pp <= -0.3:
        return f"📉 {change_pp:.1f}pp"
    return "—"


def fmt_telegram_snapshot(teams, prev_probs, market, date_str, games, injuries):
    lines = [f"📊 NBA Market Brief — {date_str}", ""]
    lines.append("🏆 Championship Odds (Polymarket)")

    sorted_teams = sorted(teams.items(), key=lambda x: x[1]["pm_prob"], reverse=True)
    for i, (team, d) in enumerate(sorted_teams[:5], 1):
        pm = d["pm_prob"] * 100
        book = d["book_prob"] * 100
        gap = d["gap"] * 100
        prev = prev_probs.get(team)
        change_pp = (d["pm_prob"] - prev) * 100 if prev is not None else None
        arrow = _overnight_arrow(change_pp) if change_pp is not None else "—"
        gap_str = f"{gap:+.1f}pp"
        lines.append(f"{i}. {team:<12} {pm:.1f}%  {arrow:<14} | Books: {book:.1f}%  GAP: {gap_str}")

    if games or injuries:
        lines.append("")
        lines.append("📰 NBA Context")
        for g in games:
            lines.append(f"• {g['winner']} def. {g['loser']} {g['winner_score']}-{g['loser_score']}")
        for inj in injuries:
            loc = f" ({inj['location']})" if inj["location"] else ""
            lines.append(f"• {inj['player']}{loc} listed {inj['status']} — {inj['team']}")

    lines.append("")
    lines.append("📊 Market Health")
    vol_m = market.get("total_vol_24hr", 0) / 1_000_000
    overround_pp = (market.get("overround", 1.0) - 1.0) * 100
    tracked = market.get("matched_teams", "?")
    lines.append(f"24h vol: ${vol_m:.1f}M | Overround: {overround_pp:.1f}pp | Markets tracked: {tracked}")

    return "\n".join(lines)
