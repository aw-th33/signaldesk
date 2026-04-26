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
