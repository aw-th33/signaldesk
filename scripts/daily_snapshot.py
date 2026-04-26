import json, os, sys, io, time, requests
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIGNALS_FILE = os.path.join(BASE_DIR, "latest_signals.json")
STATE_FILE = os.path.join(BASE_DIR, "state.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# Load .env
env_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_path):
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHANNEL = os.environ.get("TELEGRAM_CHANNEL", "")
TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY", "")
TWITTER_API_SECRET = os.environ.get("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET = os.environ.get("TWITTER_ACCESS_SECRET", "")
DRY_RUN = os.environ.get("SNAPSHOT_DRY_RUN", "0") == "1"



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
            team_name = team_block.get("displayName", "")
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


def _normalize(name):
    return name.lower().strip()


def _filter_injuries(injuries, pm_team_keys):
    pm_lookup = {_normalize(k): k for k in pm_team_keys}
    filtered = []
    for inj in injuries:
        team = inj.get("team", "")
        if _normalize(team) in pm_lookup:
            filtered.append(inj)
    return filtered


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


def fmt_twitter_snapshot(teams, prev_probs, market, date_str, games, injuries):
    sorted_teams = sorted(teams.items(), key=lambda x: x[1]["pm_prob"], reverse=True)
    top2 = sorted_teams[:2]

    lines = [f"NBA Markets — {date_str}", ""]

    team_parts = []
    for team, d in top2:
        pm = d["pm_prob"] * 100
        prev = prev_probs.get(team)
        change_str = ""
        if prev is not None:
            chg = (d["pm_prob"] - prev) * 100
            if abs(chg) >= 0.3:
                change_str = f" ({chg:+.1f}pp)"
        team_parts.append(f"{team} {pm:.1f}%{change_str}")
    lines.append(" | ".join(team_parts))

    # News hook: injury if available, otherwise biggest gap
    hook = ""
    if injuries:
        inj = injuries[0]
        loc = f" ({inj['location']})" if inj["location"] else ""
        hook = f"{inj['player']}{loc} {inj['status']} → {inj['team']} watch"
    elif teams:
        biggest_gap_team = max(teams.items(), key=lambda x: abs(x[1]["gap"]))
        team_name, d = biggest_gap_team
        gap_pp = d["gap"] * 100
        direction = "above" if gap_pp > 0 else "below"
        hook = f"Biggest gap: {team_name} {abs(gap_pp):.1f}pp {direction} books"

    if hook:
        lines.append("")
        lines.append(hook)

    lines.append("")
    lines.append("Signal Desk on Telegram 👇 @SignalDesk")

    out = "\n".join(lines)
    if len(out) > 280:
        out = out[:274] + "…"
    return out


def fmt_newsletter_snapshot(teams, prev_probs, market, date_str, games, injuries):
    lines = [f"## NBA Championship Markets — {date_str}", ""]
    lines.append("| Team | PM Prob | Change | Books | Gap | 24h Vol |")
    lines.append("|------|---------|--------|-------|-----|---------|")

    sorted_teams = sorted(teams.items(), key=lambda x: x[1]["pm_prob"], reverse=True)
    for team, d in sorted_teams:
        pm = d["pm_prob"] * 100
        book = d["book_prob"] * 100
        gap = d["gap"] * 100
        vol_k = d["vol"] / 1000
        prev = prev_probs.get(team)
        if prev is not None:
            chg = (d["pm_prob"] - prev) * 100
            change_str = f"{chg:+.1f}pp"
        else:
            change_str = "—"
        lines.append(f"| {team} | {pm:.1f}% | {change_str} | {book:.1f}% | {gap:+.1f}pp | ${vol_k:.0f}K |")

    if games:
        lines.append("")
        lines.append("### Last Night's Results")
        for g in games:
            lines.append(f"- {g['winner']} {g['winner_score']} def. {g['loser']} {g['loser_score']}")

    if injuries:
        lines.append("")
        lines.append("### Injury Watch")
        for inj in injuries:
            loc = f" ({inj['location']})" if inj["location"] else ""
            lines.append(f"- {inj['player']} ({inj['team']}) — {inj['status']}{loc}")

    lines.append("")
    vol_raw = market.get("total_vol_24hr")
    overround_raw = market.get("overround")
    tracked = market.get("matched_teams", "?")
    vol_str = f"${vol_raw / 1_000_000:.1f}M" if vol_raw is not None else "?"
    overround_str = f"{(overround_raw - 1.0) * 100:.1f}pp" if overround_raw is not None else "?"
    lines.append(f"**Market Health:** 24h vol {vol_str} | Overround {overround_str} | {tracked} teams tracked")

    return "\n".join(lines)


def post_telegram(text):
    if not BOT_TOKEN or not CHANNEL:
        print("Telegram credentials not set, skipping.")
        return
    escaped = text.replace("&", "&amp;").replace("<", "&lt;")
    if DRY_RUN:
        print(f"[DRY RUN] Telegram ({len(escaped)} chars):\n{escaped}\n")
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": CHANNEL, "text": escaped,
            "parse_mode": "HTML", "disable_web_page_preview": True,
        }, timeout=15)
        data = resp.json()
        if not data.get("ok"):
            print(f"Telegram error: {data.get('description', 'unknown')}")
        else:
            print(f"Telegram posted. Message ID: {data['result']['message_id']}")
    except Exception as e:
        print(f"Telegram post failed: {e}")


def post_twitter(text):
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET]):
        print("Twitter credentials not set, skipping.")
        return
    if DRY_RUN:
        print(f"[DRY RUN] Twitter ({len(text)} chars):\n{text}\n")
        return
    try:
        import tweepy
        client = tweepy.Client(
            consumer_key=TWITTER_API_KEY, consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN, access_token_secret=TWITTER_ACCESS_SECRET,
        )
        resp = client.create_tweet(text=text)
        print(f"Twitter posted. Tweet ID: {resp.data['id']}")
    except Exception as e:
        print(f"Twitter post failed: {e}")


def main():
    # Ensure stdout handles Unicode (needed on Windows with CP1252 default encoding).
    # Guard: only wrap when there's a raw buffer to wrap and the current encoding isn't UTF-8.
    # Skip if stdout is pytest's EncodedFile (no buffer attr that's wrappable).
    _stdout_enc = getattr(sys.stdout, "encoding", "") or ""
    if hasattr(sys.stdout, "buffer") and _stdout_enc.lower().replace("-", "") != "utf8":
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        except Exception:
            pass
    t0 = time.time()
    now = datetime.now(timezone.utc)
    # %-d is Linux-only; strip leading zero on Windows via lstrip
    date_str = now.strftime("%b %-d") if os.name != "nt" else now.strftime("%b %d").lstrip("0")
    print(f"Signal Desk Daily Snapshot — {now.isoformat()}")
    print("-" * 55)

    data = load_snapshot_data()
    prev_probs = load_prev_state()

    print("Fetching ESPN data...")
    games = fetch_espn_scores()
    injuries_raw = fetch_espn_injuries()
    injuries = _filter_injuries(injuries_raw, data.get("teams", {}).keys())
    print(f"  Games: {len(games)} | Injuries: {len(injuries_raw)} → {len(injuries)} filtered")
    teams = data["teams"]
    market = data["market"]

    tg = fmt_telegram_snapshot(teams, prev_probs, market, date_str, games, injuries)
    tw = fmt_twitter_snapshot(teams, prev_probs, market, date_str, games, injuries)
    nl = fmt_newsletter_snapshot(teams, prev_probs, market, date_str, games, injuries)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for fname, content in [
        ("snapshot_telegram.txt", tg),
        ("snapshot_twitter.txt", tw),
        ("snapshot_newsletter.txt", nl),
    ]:
        path = os.path.join(OUTPUT_DIR, fname)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Written: {path}")

    print("\nPosting...")
    post_telegram(tg)
    post_twitter(tw)

    print(f"\nDone in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
