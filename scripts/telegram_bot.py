import os, sys, io, json, requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
SIGNALS_FILE = os.path.join(BASE_DIR, "latest_signals.json")
TELEGRAM_FILE = os.path.join(OUTPUT_DIR, "telegram.txt")

# Load .env
env_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHANNEL = os.environ.get("TELEGRAM_CHANNEL", "")  # e.g. @SignalDeskNBA
DRY_RUN = os.environ.get("TELEGRAM_DRY_RUN", "0") == "1"


def send_telegram(text, token, chat_id):
    url = "https://api.telegram.org/bot{}/sendMessage".format(token)
    resp = requests.post(url, json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }, timeout=15)
    data = resp.json()
    if not data.get("ok"):
        raise Exception("Telegram API error: {}".format(data.get("description", "unknown")))
    return data


def main():
    if not BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN not set in .env")
        sys.exit(1)
    if not CHANNEL:
        print("TELEGRAM_CHANNEL not set in .env")
        sys.exit(1)

    if os.path.exists(SIGNALS_FILE):
        with open(SIGNALS_FILE, encoding="utf-8") as f:
            n = len(json.load(f).get("signals", []))
        if n == 0:
            print("No signals, skipping Telegram post.")
            return

    if not os.path.exists(TELEGRAM_FILE):
        print("No telegram.txt found. Run alert_formatter.py first.")
        sys.exit(1)

    with open(TELEGRAM_FILE, encoding="utf-8") as f:
        text = f.read()

    if not text.strip():
        print("Empty message, nothing to post.")
        return

    # Escape < and & for HTML parse mode; Telegram handles > and quotes fine
    escaped = text.replace("&", "&amp;").replace("<", "&lt;")

    if DRY_RUN:
        print("[DRY RUN] Would post to {} ({} chars):".format(CHANNEL, len(escaped)))
        print("-" * 50)
        print(text)
        print("-" * 50)
        return

    print("Posting to {} ({} chars)...".format(CHANNEL, len(escaped)))
    result = send_telegram(escaped, BOT_TOKEN, CHANNEL)
    msg_id = result.get("result", {}).get("message_id", "?")
    print("Posted successfully. Message ID: {}".format(msg_id))


if __name__ == "__main__":
    main()
