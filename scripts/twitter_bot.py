import os, sys, io, json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
SIGNALS_FILE = os.path.join(BASE_DIR, "latest_signals.json")
TWITTER_FILE = os.path.join(OUTPUT_DIR, "twitter.txt")

env_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))

TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY", "")
TWITTER_API_SECRET = os.environ.get("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET = os.environ.get("TWITTER_ACCESS_SECRET", "")
DRY_RUN = os.environ.get("TWITTER_DRY_RUN", "0") == "1"


def main():
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET]):
        print("Twitter credentials not set in .env. Skipping.")
        print("  Required: TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET")
        return

    if os.path.exists(SIGNALS_FILE):
        with open(SIGNALS_FILE, encoding="utf-8") as f:
            n = len(json.load(f).get("signals", []))
        if n == 0:
            print("No signals, skipping Twitter post.")
            return

    if not os.path.exists(TWITTER_FILE):
        print("No twitter.txt found. Run alert_formatter.py first.")
        return

    with open(TWITTER_FILE, encoding="utf-8") as f:
        text = f.read().strip()

    if not text:
        print("Empty twitter message, nothing to post.")
        return

    if DRY_RUN:
        print("[DRY RUN] Would post tweet ({} chars):".format(len(text)))
        print("-" * 50)
        print(text)
        print("-" * 50)
        return

    try:
        import tweepy
    except ImportError:
        print("tweepy not installed. Run: pip install tweepy")
        return

    client = tweepy.Client(
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_SECRET,
    )

    print("Posting tweet ({} chars)...".format(len(text)))
    resp = client.create_tweet(text=text)
    tweet_id = resp.data.get("id", "?")
    print("Posted. Tweet ID: {}".format(tweet_id))


if __name__ == "__main__":
    main()
