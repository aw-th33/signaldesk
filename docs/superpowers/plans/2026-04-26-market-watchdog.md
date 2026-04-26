# Market Watchdog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Standalone Telegram bot that lets users watch any Polymarket market and receive DMs when prob/vol/spread thresholds are breached.

**Architecture:** 4 modules (config_handler, market_poller, alert_evaluator, alert_delivery) chained by orchestrator. GitHub Actions cron every 10 min. State in `watchlist.json` persisted via Actions cache. No Odds API — 100% Gamma API.

**Tech Stack:** Python 3, requests, pytest. Telegram Bot API (polling). Polymarket Gamma API (free/public).

**Repo:** `github.com/aw-th33/market-watchdog` (private, empty)

---

## File Structure

```
market-watchdog/
├── scripts/
│   ├── state.py             # read/save watchlist.json, load .env
│   ├── config_handler.py    # parse /watch, /unwatch, /threshold etc.
│   ├── market_poller.py     # fetch Gamma API for watched slugs
│   ├── alert_evaluator.py   # check thresholds, apply cooldown
│   ├── alert_delivery.py    # send Telegram DM
│   └── orchestrator.py      # chain: config → poll → eval → deliver
├── tests/
│   ├── test_state.py
│   ├── test_config_handler.py
│   ├── test_market_poller.py
│   ├── test_alert_evaluator.py
│   ├── test_alert_delivery.py
│   └── test_orchestrator.py
├── watchlist.json
├── requirements.txt
├── pytest.ini
├── .env.example
├── .gitignore
└── .github/workflows/scheduler.yml
```

---

### Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`, `.env.example`, `.gitignore`, `pytest.ini`, `scripts/state.py`, `watchlist.json`
- Create test: `tests/test_state.py`
- Create: `tests/__init__.py`, `scripts/__init__.py`

- [ ] **Step 1: Clone repo and set up structure**

```bash
git clone https://github.com/aw-th33/market-watchdog.git
cd market-watchdog
mkdir scripts tests
```

- [ ] **Step 2: Write `requirements.txt`**

```
requests>=2.28
pytest>=7.0
```

- [ ] **Step 3: Write `.gitignore`**

```
.env
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 4: Write `.env.example`**

```
TELEGRAM_BOT_TOKEN=
```

- [ ] **Step 5: Write `pytest.ini`**

```ini
[pytest]
pythonpath = scripts
```

- [ ] **Step 6: Write initial `watchlist.json`**

```json
{
  "users": {}
}
```

- [ ] **Step 7: Write `scripts/state.py`**

```python
import json, os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCHLIST_FILE = os.path.join(BASE_DIR, "watchlist.json")


def load_env():
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def load_watchlist():
    if not os.path.exists(WATCHLIST_FILE):
        return {"users": {}}
    with open(WATCHLIST_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_watchlist(data):
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
```

- [ ] **Step 8: Write `tests/test_state.py`**

```python
import json
import os
import tempfile
import state
import state as state_mod


def test_load_watchlist_empty_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"users": {}}')
        tmp = f.name
    try:
        state_mod.WATCHLIST_FILE = tmp
        data = state.load_watchlist()
        assert data == {"users": {}}
    finally:
        os.unlink(tmp)


def test_save_and_load_roundtrip():
    data = {"users": {"123": {"alerts_paused": False, "markets": {}}}}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        tmp = f.name
    try:
        state_mod.WATCHLIST_FILE = tmp
        state.save_watchlist(data)
        loaded = state.load_watchlist()
        assert loaded == data
    finally:
        os.unlink(tmp)
```

- [ ] **Step 9: Run tests, verify they pass**

```bash
pip install -r requirements.txt
python -m pytest tests/test_state.py -v
```

Expected: 2 passed

- [ ] **Step 10: Commit**

```bash
git add .
git commit -m "feat: project scaffold — state module, watchlist, config"
```

---

### Task 2: Market Poller

**Files:**
- Create: `scripts/market_poller.py`
- Create test: `tests/test_market_poller.py`

- [ ] **Step 1: Write failing test**

`tests/test_market_poller.py`:

```python
import market_poller


def test_collect_unique_slugs():
    """Given a watchlist, returns set of unique event slugs."""
    watchlist = {
        "users": {
            "u1": {
                "alerts_paused": False,
                "markets": {
                    "2026-nba-champion_oklahoma-city-thunder": {
                        "slug": "2026-nba-champion",
                        "token": "oklahoma-city-thunder",
                    },
                    "will-btc-hit-100k_yes": {
                        "slug": "will-btc-hit-100k",
                        "token": "yes",
                    },
                },
            },
            "u2": {
                "alerts_paused": False,
                "markets": {
                    "2026-nba-champion_boston-celtics": {
                        "slug": "2026-nba-champion",
                        "token": "boston-celtics",
                    },
                },
            },
        }
    }
    slugs = market_poller.collect_slugs(watchlist)
    assert slugs == {"2026-nba-champion", "will-btc-hit-100k"}


def test_parse_event_markets():
    """Parses a Gamma API event response into a dict of token->data."""
    event = {
        "title": "2026 NBA Champion",
        "markets": [
            {
                "question": "Will OKC Thunder win the 2026 NBA Finals?",
                "outcomePrices": "[0.525, 0.475]",
                "volumeNum": 100000.0,
                "volume24hr": 5000.0,
                "liquidityNum": 20000.0,
                "clobTokenIds": '["token-okc-yes", "token-okc-no"]',
            }
        ],
    }
    result = market_poller.parse_event(event)
    assert len(result) == 1
    token_key = list(result.keys())[0]
    market_data = result[token_key]
    assert market_data["pm_prob"] == 0.525
    assert market_data["vol_24hr"] == 5000.0
    assert market_data["spread"] is not None


def test_parse_event_missing_prices():
    """Market with empty prices yields prob 0."""
    event = {
        "title": "Test Event",
        "markets": [
            {
                "question": "Will something happen?",
                "outcomePrices": "[]",
                "volumeNum": 0,
                "volume24hr": 0,
                "clobTokenIds": "[]",
            }
        ],
    }
    result = market_poller.parse_event(event)
    token_key = list(result.keys())[0]
    assert result[token_key]["pm_prob"] == 0.0
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_market_poller.py -v
```

Expected: FAIL (module not found or function not defined)

- [ ] **Step 3: Write `scripts/market_poller.py`**

```python
import json
import os
import sys
import io
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PM_GAMMA = "https://gamma-api.polymarket.com"


def collect_slugs(watchlist):
    slugs = set()
    for user_id, data in watchlist.get("users", {}).items():
        for market_key, m in data.get("markets", {}).items():
            slugs.add(m.get("slug", ""))
    slugs.discard("")
    return slugs


def parse_event(event):
    markets = event.get("markets", [])
    result = {}
    for m in markets:
        question = m.get("question") or ""
        token_ids = json.loads(m.get("clobTokenIds", "[]"))
        if not token_ids:
            continue
        token_key = token_ids[0]
        prices = json.loads(m.get("outcomePrices", "[]"))
        prob = float(prices[0]) if prices else 0.0
        vol_24hr = float(m.get("volume24hr", 0) or 0)
        result[token_key] = {
            "question": question,
            "pm_prob": prob,
            "vol_24hr": vol_24hr,
            "vol_total": float(m.get("volumeNum", 0) or 0),
            "spread": float(m.get("spread", 0) or 0) if m.get("spread") is not None else 0.0,
            "liq": float(m.get("liquidityNum", 0) or 0),
        }
    return result


def fetch_slugs(slugs):
    data = {}
    for slug in slugs:
        try:
            resp = requests.get(f"{PM_GAMMA}/events/slug/{slug}", timeout=15)
            if resp.status_code != 200:
                print(f"Gamma API error for {slug}: {resp.status_code}")
                continue
            event = resp.json()
            data[slug] = parse_event(event)
        except Exception as e:
            print(f"Failed to fetch {slug}: {e}")
    return data
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_market_poller.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/market_poller.py tests/test_market_poller.py
git commit -m "feat: market poller — Gamma API fetch + slug collection"
```

---

### Task 3: Alert Evaluator

**Files:**
- Create: `scripts/alert_evaluator.py`
- Create test: `tests/test_alert_evaluator.py`

- [ ] **Step 1: Write failing test**

`tests/test_alert_evaluator.py`:

```python
from datetime import datetime, timezone, timedelta
import alert_evaluator


def test_prob_move_triggered():
    user_market = {
        "label": "OKC Thunder",
        "slug": "2026-nba-champion",
        "token": "token-okc",
        "thresholds": {"prob_move": 0.03, "vol_spike_ratio": 3.0, "spread_above": 0.01},
        "cooldown_min": 30,
        "last_prob": 0.50,
        "last_alert_at": None,
    }
    current = {"pm_prob": 0.54, "vol_24hr": 1000.0, "spread": 0.005}
    alerts = alert_evaluator.evaluate("u1", "okc", user_market, current)
    assert len(alerts) == 1
    assert "Prob" in alerts[0]
    assert "+4.0pp" in alerts[0]


def test_no_trigger_below_threshold():
    user_market = {
        "label": "OKC Thunder",
        "slug": "2026-nba-champion",
        "token": "token-okc",
        "thresholds": {"prob_move": 0.03, "vol_spike_ratio": 3.0, "spread_above": 0.01},
        "cooldown_min": 30,
        "last_prob": 0.50,
        "last_alert_at": None,
    }
    current = {"pm_prob": 0.51, "vol_24hr": 1000.0, "spread": 0.005}
    alerts = alert_evaluator.evaluate("u1", "okc", user_market, current)
    assert alerts == []


def test_volume_spike_triggered():
    user_market = {
        "label": "OKC Thunder",
        "slug": "2026-nba-champion",
        "token": "token-okc",
        "thresholds": {"prob_move": 0.03, "vol_spike_ratio": 3.0, "spread_above": 0.01},
        "cooldown_min": 30,
        "last_vol_24hr": 1000.0,
        "last_prob": 0.50,
        "last_alert_at": None,
    }
    current = {"pm_prob": 0.50, "vol_24hr": 5000.0, "spread": 0.005}
    alerts = alert_evaluator.evaluate("u1", "okc", user_market, current)
    assert len(alerts) == 1
    assert "vol" in alerts[0].lower() or "Vol" in alerts[0]


def test_spread_triggered():
    user_market = {
        "label": "OKC Thunder",
        "slug": "2026-nba-champion",
        "token": "token-okc",
        "thresholds": {"prob_move": 0.03, "vol_spike_ratio": 3.0, "spread_above": 0.01},
        "cooldown_min": 30,
        "last_spread": 0.005,
        "last_prob": 0.50,
        "last_alert_at": None,
    }
    current = {"pm_prob": 0.50, "vol_24hr": 1000.0, "spread": 0.02}
    alerts = alert_evaluator.evaluate("u1", "okc", user_market, current)
    assert len(alerts) == 1
    assert "spread" in alerts[0].lower() or "Spread" in alerts[0]


def test_cooldown_blocks_alert():
    recent = datetime.now(timezone.utc) - timedelta(minutes=10)
    user_market = {
        "label": "OKC Thunder",
        "slug": "2026-nba-champion",
        "token": "token-okc",
        "thresholds": {"prob_move": 0.03, "vol_spike_ratio": 3.0, "spread_above": 0.01},
        "cooldown_min": 30,
        "last_prob": 0.50,
        "last_alert_at": recent.isoformat(),
    }
    current = {"pm_prob": 0.54, "vol_24hr": 1000.0, "spread": 0.005}
    alerts = alert_evaluator.evaluate("u1", "okc", user_market, current)
    assert alerts == []


def test_multiple_triggers():
    user_market = {
        "label": "OKC Thunder",
        "slug": "2026-nba-champion",
        "token": "token-okc",
        "thresholds": {"prob_move": 0.03, "vol_spike_ratio": 3.0, "spread_above": 0.01},
        "cooldown_min": 30,
        "last_prob": 0.50,
        "last_vol_24hr": 500.0,
        "last_spread": 0.003,
        "last_alert_at": None,
    }
    current = {"pm_prob": 0.54, "vol_24hr": 5000.0, "spread": 0.02}
    alerts = alert_evaluator.evaluate("u1", "okc", user_market, current)
    assert len(alerts) == 3
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_alert_evaluator.py -v
```

Expected: FAIL

- [ ] **Step 3: Write `scripts/alert_evaluator.py`**

```python
from datetime import datetime, timezone, timedelta


def evaluate(user_id, market_key, user_market, current):
    thresholds = user_market.get("thresholds", {})
    alerts = []

    # Prob move
    prob_threshold = thresholds.get("prob_move", 0.03)
    last_prob = user_market.get("last_prob", 0)
    current_prob = current.get("pm_prob", 0)
    if last_prob is not None and abs(current_prob - last_prob) >= prob_threshold:
        change_pp = (current_prob - last_prob) * 100
        direction = "up" if change_pp >= 0 else "down"
        arrow = "+" if change_pp >= 0 else ""
        alerts.append(
            f"Prob {direction} {arrow}{change_pp:.1f}pp ({last_prob*100:.1f}% -> {current_prob*100:.1f}%)"
        )

    # Volume spike
    vol_threshold = thresholds.get("vol_spike_ratio", 3.0)
    last_vol = user_market.get("last_vol_24hr")
    current_vol = current.get("vol_24hr", 0)
    if last_vol and last_vol > 0 and current_vol > 0:
        ratio = current_vol / last_vol
        if ratio >= vol_threshold:
            alerts.append(
                f"Vol spike {ratio:.1f}x (24h ${current_vol/1000:.0f}K vs ${last_vol/1000:.0f}K avg)"
            )

    # Spread breach
    spread_threshold = thresholds.get("spread_above", 0.01)
    current_spread = current.get("spread", 0)
    if current_spread >= spread_threshold:
        alerts.append(f"Spread widened to {current_spread:.3f} (threshold {spread_threshold:.3f})")

    # Cooldown check
    if alerts:
        last_alert = user_market.get("last_alert_at")
        cooldown = user_market.get("cooldown_min", 30)
        if last_alert:
            try:
                last_dt = datetime.fromisoformat(last_alert.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) - last_dt < timedelta(minutes=cooldown):
                    return []
            except Exception:
                pass

    return alerts
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_alert_evaluator.py -v
```

Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/alert_evaluator.py tests/test_alert_evaluator.py
git commit -m "feat: alert evaluator — prob/vol/spread thresholds + cooldown"
```

---

### Task 4: Alert Delivery

**Files:**
- Create: `scripts/alert_delivery.py`
- Create test: `tests/test_alert_delivery.py`

- [ ] **Step 1: Write failing test**

`tests/test_alert_delivery.py`:

```python
import alert_delivery


def test_format_alert_message():
    alerts = [
        "Prob up +4.2pp (48.5% -> 52.7%)",
        "Vol spike 5.0x (24h $50K vs $10K avg)",
    ]
    label = "OKC Thunder"
    result = alert_delivery.format_message(label, alerts)
    assert "OKC Thunder" in result
    assert "Prob up" in result
    assert "Vol spike" in result
    assert result.startswith("🔔")


def test_format_alert_message_single():
    alerts = ["Spread widened to 0.025 (threshold 0.010)"]
    label = "BTC > 100K"
    result = alert_delivery.format_message(label, alerts)
    assert label in result
    assert "Spread" in result
    assert "\n" not in result.strip()


def test_update_state_after_alert():
    from datetime import datetime, timezone

    user_market = {
        "label": "OKC Thunder",
        "last_prob": 0.50,
        "last_alert_at": None,
    }
    current = {"pm_prob": 0.54, "vol_24hr": 5000.0, "spread": 0.005}
    alert_delivery.update_market_state(user_market, current)
    assert user_market["last_prob"] == 0.54
    assert user_market["last_alert_at"] is not None
    assert user_market["last_vol_24hr"] == 5000.0
    assert user_market["last_spread"] == 0.005
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_alert_delivery.py -v
```

Expected: FAIL

- [ ] **Step 3: Write `scripts/alert_delivery.py`**

```python
import requests
import os
import sys
import io
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def format_message(label, alerts):
    lines = [
        f"\U0001F514 {label}",
    ]
    for alert in alerts:
        lines.append(alert)
    return "\n".join(lines)


def send_telegram_dm(text, token, user_id, dry_run=False):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": user_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if dry_run:
        print(f"[DRY RUN] Would DM user {user_id}: {text[:80]}...")
        return {"ok": True, "result": {"message_id": 0}}
    resp = requests.post(url, json=payload, timeout=15)
    data = resp.json()
    if not data.get("ok"):
        raise Exception(f"Telegram API error: {data.get('description', 'unknown')}")
    return data


def update_market_state(user_market, current):
    user_market["last_prob"] = current.get("pm_prob", 0)
    user_market["last_vol_24hr"] = current.get("vol_24hr", 0)
    user_market["last_spread"] = current.get("spread", 0)
    user_market["last_alert_at"] = datetime.now(timezone.utc).isoformat()


def deliver_alerts(to_send, token, watchlist, dry_run=False):
    """to_send: list of (user_id, market_key, alerts, label) tuples"""
    users = watchlist.setdefault("users", {})
    for user_id, market_key, alerts, label in to_send:
        msg = format_message(label, alerts)
        try:
            send_telegram_dm(msg, token, user_id, dry_run=dry_run)
        except Exception as e:
            print(f"Failed to send DM to {user_id}: {e}")
            continue
        user_data = users.get(user_id)
        if user_data and market_key in user_data.get("markets", {}):
            current = {}
            update_market_state(user_data["markets"][market_key], current)
        print(f"Sent alert to {user_id} for {label}")
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_alert_delivery.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/alert_delivery.py tests/test_alert_delivery.py
git commit -m "feat: alert delivery — format, send DM, update state"
```

---

### Task 5: Config Handler

**Files:**
- Create: `scripts/config_handler.py`
- Create test: `tests/test_config_handler.py`

- [ ] **Step 1: Write failing test**

`tests/test_config_handler.py`:

```python
from datetime import datetime, timezone
import copy
import config_handler


def make_users():
    return {
        "users": {
            "123": {
                "alerts_paused": False,
                "markets": {},
            }
        }
    }


def test_handle_watch_adds_market():
    wl = make_users()
    updates = copy.deepcopy(wl)  # preserve original for comparison
    result = config_handler.handle_watch("123", "2026-nba-champion", "oklahoma-city-thunder", "OKC Thunder", wl)
    assert "OKC Thunder" in result
    assert "123" in wl["users"]
    markets = wl["users"]["123"]["markets"]
    assert len(markets) == 1
    key = list(markets.keys())[0]
    m = markets[key]
    assert m["label"] == "OKC Thunder"
    assert m["slug"] == "2026-nba-champion"
    assert m["token"] == "oklahoma-city-thunder"
    assert m["thresholds"]["prob_move"] == 0.03
    assert m["thresholds"]["vol_spike_ratio"] == 3.0
    assert m["thresholds"]["spread_above"] == 0.01
    assert m["cooldown_min"] == 30


def test_handle_unwatch_removes_market():
    wl = {
        "users": {
            "123": {
                "alerts_paused": False,
                "markets": {
                    "2026-nba-champion_oklahoma-city-thunder": {
                        "label": "OKC Thunder",
                        "slug": "2026-nba-champion",
                        "token": "oklahoma-city-thunder",
                        "thresholds": {"prob_move": 0.03, "vol_spike_ratio": 3.0, "spread_above": 0.01},
                        "cooldown_min": 30,
                        "last_prob": 0.5,
                        "last_alert_at": None,
                    }
                },
            }
        }
    }
    result = config_handler.handle_unwatch("123", "OKC Thunder", wl)
    assert "removed" in result.lower()
    assert len(wl["users"]["123"]["markets"]) == 0


def test_handle_unwatch_partial_match():
    wl = {
        "users": {
            "123": {
                "alerts_paused": False,
                "markets": {
                    "slug-a_token-x": {
                        "label": "Market X",
                        "slug": "slug-a",
                        "token": "token-x",
                        "thresholds": {"prob_move": 0.03, "vol_spike_ratio": 3.0, "spread_above": 0.01},
                        "cooldown_min": 30,
                        "last_prob": 0.5,
                        "last_alert_at": None,
                    }
                },
            }
        }
    }
    result = config_handler.handle_unwatch("123", "x", wl)
    assert "removed" in result.lower()


def test_handle_list_shows_markets():
    wl = {
        "users": {
            "123": {
                "alerts_paused": False,
                "markets": {
                    "slug-a_token-x": {
                        "label": "Market X",
                        "slug": "slug-a",
                        "token": "token-x",
                        "thresholds": {"prob_move": 0.03, "vol_spike_ratio": 3.0, "spread_above": 0.01},
                        "cooldown_min": 30,
                        "last_prob": 0.5,
                        "last_alert_at": None,
                    }
                },
            }
        }
    }
    result = config_handler.handle_list("123", wl)
    assert "Market X" in result


def test_handle_list_empty():
    wl = make_users()
    result = config_handler.handle_list("123", wl)
    assert "no markets" in result.lower()


def test_handle_threshold_sets_value():
    wl = {
        "users": {
            "123": {
                "alerts_paused": False,
                "markets": {
                    "slug-a_token-x": {
                        "label": "Market X",
                        "slug": "slug-a",
                        "token": "token-x",
                        "thresholds": {"prob_move": 0.03, "vol_spike_ratio": 3.0, "spread_above": 0.01},
                        "cooldown_min": 30,
                        "last_prob": 0.5,
                        "last_alert_at": None,
                    }
                },
            }
        }
    }
    result = config_handler.handle_threshold("123", "Market X", "prob", "0.05", wl)
    assert "0.05" in result
    market = list(wl["users"]["123"]["markets"].values())[0]
    assert market["thresholds"]["prob_move"] == 0.05


def test_handle_threshold_cooldown():
    wl = {
        "users": {
            "123": {
                "alerts_paused": False,
                "markets": {
                    "slug-a_token-x": {
                        "label": "Market X",
                        "slug": "slug-a",
                        "token": "token-x",
                        "thresholds": {"prob_move": 0.03, "vol_spike_ratio": 3.0, "spread_above": 0.01},
                        "cooldown_min": 30,
                        "last_prob": 0.5,
                        "last_alert_at": None,
                    }
                },
            }
        }
    }
    result = config_handler.handle_threshold("123", "Market X", "cooldown", "60", wl)
    assert "60" in result
    market = list(wl["users"]["123"]["markets"].values())[0]
    assert market["cooldown_min"] == 60


def test_handle_pause_resume():
    wl = make_users()
    r1 = config_handler.handle_pause("123", wl)
    assert wl["users"]["123"]["alerts_paused"] is True
    assert "paused" in r1.lower()

    r2 = config_handler.handle_resume("123", wl)
    assert wl["users"]["123"]["alerts_paused"] is False
    assert "resumed" in r2.lower()


def test_default_market():
    m = config_handler.default_market("OKC Thunder", "2026-nba-champion", "oklahoma-city-thunder")
    assert m["label"] == "OKC Thunder"
    assert m["slug"] == "2026-nba-champion"
    assert m["token"] == "oklahoma-city-thunder"
    assert m["thresholds"]["prob_move"] == 0.03
    assert m["cooldown_min"] == 30
    assert m["last_alert_at"] is None
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_config_handler.py -v
```

Expected: FAIL

- [ ] **Step 3: Write `scripts/config_handler.py`**

```python
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def default_market(label, slug, token):
    return {
        "label": label,
        "slug": slug,
        "token": token,
        "thresholds": {
            "prob_move": 0.03,
            "vol_spike_ratio": 3.0,
            "spread_above": 0.01,
        },
        "cooldown_min": 30,
        "last_prob": None,
        "last_vol_24hr": None,
        "last_spread": None,
        "last_alert_at": None,
    }


def ensure_user(watchlist, user_id):
    users = watchlist.setdefault("users", {})
    if user_id not in users:
        users[user_id] = {"alerts_paused": False, "markets": {}}
    return users[user_id]


def handle_watch(user_id, slug, token, label, watchlist):
    user = ensure_user(watchlist, user_id)
    market_key = f"{slug}_{token}"
    if market_key in user["markets"]:
        return f"Already watching '{label}'."
    user["markets"][market_key] = default_market(label, slug, token)
    return f"Now watching '{label}'. Default thresholds: prob_move=3pp, vol_spike=3x, spread_above=1%. Use /threshold to adjust."


def handle_unwatch(user_id, label_query, watchlist):
    user = ensure_user(watchlist, user_id)
    query_lower = label_query.lower()
    for key, m in list(user["markets"].items()):
        if query_lower in m.get("label", "").lower():
            del user["markets"][key]
            return f"Removed '{m['label']}' from your watchlist."
    return f"No watched market matching '{label_query}'."


def handle_list(user_id, watchlist):
    user = ensure_user(watchlist, user_id)
    markets = user.get("markets", {})
    if not markets:
        return "You are not watching any markets. Use /watch to add one."
    lines = ["Your watched markets:"]
    for key, m in markets.items():
        t = m.get("thresholds", {})
        status = "PAUSED" if user.get("alerts_paused") else "active"
        lines.append(
            f"  • {m['label']} [{status}]\n"
            f"    prob_move={t.get('prob_move', 0.03):.2f}pp, "
            f"vol_spike={t.get('vol_spike_ratio', 3.0):.1f}x, "
            f"spread_above={t.get('spread_above', 0.01):.3f}, "
            f"cooldown={m.get('cooldown_min', 30)}m"
        )
    return "\n".join(lines)


def handle_threshold(user_id, label_query, thresh_type, value_str, watchlist):
    user = ensure_user(watchlist, user_id)
    try:
        value = float(value_str)
    except ValueError:
        return f"Invalid value '{value_str}'. Use a number."

    thresh_map = {
        "prob": "prob_move",
        "vol": "vol_spike_ratio",
        "spread": "spread_above",
        "cooldown": None,
    }

    if thresh_type not in thresh_map:
        return f"Unknown threshold type '{thresh_type}'. Use: prob, vol, spread, cooldown."

    query_lower = label_query.lower()
    for key, m in user.get("markets", {}).items():
        if query_lower in m.get("label", "").lower():
            if thresh_type == "cooldown":
                m["cooldown_min"] = int(value)
            else:
                m["thresholds"][thresh_map[thresh_type]] = value
            return f"Updated {thresh_type} for '{m['label']}' to {value}."
    return f"No watched market matching '{label_query}'."


def handle_pause(user_id, watchlist):
    user = ensure_user(watchlist, user_id)
    user["alerts_paused"] = True
    return "Alerts paused. Use /resume to reactivate."


def handle_resume(user_id, watchlist):
    user = ensure_user(watchlist, user_id)
    user["alerts_paused"] = False
    return "Alerts resumed. You will receive alerts again."


def handle_help():
    return (
        "Market Watchdog commands:\n"
        "/watch <query> — Search and add a market\n"
        "/unwatch <name> — Remove a market\n"
        "/list — Show your watched markets\n"
        "/threshold <market> <type> <value> — Set threshold (types: prob, vol, spread, cooldown)\n"
        "/pause /resume — Stop/start alerts\n"
        "/help — This message"
    )


def search_markets(query):
    import requests
    url = f"https://gamma-api.polymarket.com/events/search?query={query}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return []
        return resp.json()[:5]
    except Exception:
        return []
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_config_handler.py -v
```

Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/config_handler.py tests/test_config_handler.py
git commit -m "feat: config handler — /watch, /unwatch, /threshold, /list, /pause"
```

---

### Task 6: Orchestrator

**Files:**
- Create: `scripts/orchestrator.py`
- Create test: `tests/test_orchestrator.py`

- [ ] **Step 1: Write failing test**

`tests/test_orchestrator.py`:

```python
import os
import tempfile
import json
import orchestrator


def test_parse_command():
    update = {
        "message": {
            "message_id": 1,
            "from": {"id": 123, "first_name": "Test"},
            "chat": {"id": 123},
            "text": "/watch Lakers",
            "entities": [{"offset": 0, "length": 6, "type": "bot_command"}],
        }
    }
    results = []
    orchestrator.process_telegram_update(update, {"users": {}}, results)
    assert len(results) == 1
    assert results[0][0] == "123"


def test_parse_help():
    update = {
        "message": {
            "message_id": 2,
            "from": {"id": 456},
            "chat": {"id": 456},
            "text": "/help",
            "entities": [{"offset": 0, "length": 5, "type": "bot_command"}],
        }
    }
    results = []
    orchestrator.process_telegram_update(update, {"users": {}}, results)
    assert len(results) == 1
    assert "watch" in results[0][1].lower() or "add" in results[0][1].lower()


def test_ignore_non_command():
    update = {"message": {"message_id": 3, "from": {"id": 123}, "chat": {"id": 123}, "text": "hello there"}}
    results = []
    orchestrator.process_telegram_update(update, {"users": {}}, results)
    assert results == []


def test_build_alert_batch():
    watchlist = {
        "users": {
            "123": {
                "alerts_paused": False,
                "markets": {
                    "slug-a_token-x": {
                        "label": "Market X",
                        "slug": "slug-a",
                        "token": "token-x",
                        "thresholds": {"prob_move": 0.03, "vol_spike_ratio": 3.0, "spread_above": 0.01},
                        "cooldown_min": 30,
                        "last_prob": 0.50,
                        "last_vol_24hr": 500.0,
                        "last_spread": 0.005,
                        "last_alert_at": None,
                    }
                },
            },
            "456": {
                "alerts_paused": True,
                "markets": {
                    "slug-b_token-y": {
                        "label": "Market Y",
                        "slug": "slug-b",
                        "token": "token-y",
                        "thresholds": {"prob_move": 0.03, "vol_spike_ratio": 3.0, "spread_above": 0.01},
                        "cooldown_min": 30,
                        "last_prob": 0.50,
                        "last_vol_24hr": 500.0,
                        "last_spread": 0.005,
                        "last_alert_at": None,
                    }
                },
            },
        }
    }
    # market_data maps slug -> {token: market_data}
    market_data = {
        "slug-a": {"token-x": {"pm_prob": 0.54, "vol_24hr": 5000.0, "spread": 0.02}},
        "slug-b": {"token-y": {"pm_prob": 0.54, "vol_24hr": 5000.0, "spread": 0.02}},
    }
    batch = orchestrator.build_alert_batch(watchlist, market_data)
    assert len(batch) == 1  # only user 123 (456 is paused)
    user_id, market_key, alerts, label = batch[0]
    assert user_id == "123"
    assert label == "Market X"
    assert len(alerts) > 0
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest tests/test_orchestrator.py -v
```

Expected: FAIL

- [ ] **Step 3: Write `scripts/orchestrator.py`**

```python
import os
import sys
import io
import json
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from config_handler import (
    handle_watch, handle_unwatch, handle_list, handle_threshold,
    handle_pause, handle_resume, handle_help,
    search_markets, ensure_user,
)
from market_poller import collect_slugs, fetch_slugs
from alert_evaluator import evaluate
from alert_delivery import deliver_alerts, format_message, send_telegram_dm, update_market_state
from state import load_watchlist, save_watchlist, load_env

TELEGRAM_API = "https://api.telegram.org/bot"


def get_updates(token, offset=None):
    params = {"timeout": 5, "allowed_updates": ["message"]}
    if offset is not None:
        params["offset"] = offset
    url = f"{TELEGRAM_API}{token}/getUpdates"
    resp = requests.get(url, params=params, timeout=30)
    if resp.status_code != 200:
        print(f"getUpdates error: {resp.status_code}")
        return [], offset
    data = resp.json()
    updates = data.get("result", [])
    if updates:
        offset = updates[-1]["update_id"] + 1
    return updates, offset


def process_telegram_update(update, watchlist, responses):
    msg = update.get("message", {})
    if not msg:
        return
    text = msg.get("text", "")
    entities = msg.get("entities", [])
    if not entities or entities[0].get("type") != "bot_command":
        return
    command = text.split()[0].lower().split("@")[0]
    user_id = str(msg["from"]["id"])
    user = ensure_user(watchlist, user_id)
    response = None

    if command == "/watch":
        query = text.split(maxsplit=1)[1] if len(text.split()) > 1 else ""
        if not query:
            response = "Usage: /watch <market name>"
        else:
            results = search_markets(query)
            if not results:
                response = f"No markets found for '{query}'."
            elif len(results) == 1:
                ev = results[0]
                slug = ev.get("slug", "")
                title = ev.get("title", slug)
                markets = ev.get("markets", [])
                for m in markets:
                    token_ids = json.loads(m.get("clobTokenIds", "[]"))
                    if token_ids:
                        label = m.get("question", title).replace("Will ", "").strip()
                        response = handle_watch(user_id, slug, token_ids[0], label, watchlist)
                        break
                else:
                    response = f"Found event '{title}' but couldn't extract market token."
            else:
                lines = ["Multiple markets found. Reply with the number:"]
                for i, ev in enumerate(results[:5]):
                    lines.append(f"{i+1}. {ev.get('title', ev.get('slug', '?'))}")
                response = "\n".join(lines)
                # Store search results temporarily for numeric selection
                user["_search_results"] = results[:5]

    elif command == "/unwatch":
        query = text.split(maxsplit=1)[1] if len(text.split()) > 1 else ""
        response = handle_unwatch(user_id, query, watchlist) if query else "Usage: /unwatch <market name>"

    elif command == "/list":
        response = handle_list(user_id, watchlist)

    elif command == "/threshold":
        parts = text.split()
        if len(parts) < 4:
            response = "Usage: /threshold <market> <type> <value>\nTypes: prob, vol, spread, cooldown"
        else:
            response = handle_threshold(user_id, parts[1], parts[2], parts[3], watchlist)

    elif command == "/pause":
        response = handle_pause(user_id, watchlist)

    elif command == "/resume":
        response = handle_resume(user_id, watchlist)

    elif command == "/help":
        response = handle_help()

    if response:
        responses.append((str(msg["chat"]["id"]), response))


def build_alert_batch(watchlist, market_data):
    batch = []
    for user_id, data in watchlist.get("users", {}).items():
        if data.get("alerts_paused"):
            continue
        for market_key, user_market in data.get("markets", {}).items():
            slug = user_market.get("slug", "")
            token = user_market.get("token", "")
            slug_data = market_data.get(slug, {})
            current = slug_data.get(token)
            if not current:
                continue
            alerts = evaluate(user_id, market_key, user_market, current)
            if alerts:
                batch.append((user_id, market_key, alerts, user_market["label"]))
    return batch


def main():
    load_env()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        print("TELEGRAM_BOT_TOKEN not set in .env")
        sys.exit(1)

    watchlist = load_watchlist()
    responses = []

    # --- 1. Process incoming Telegram commands ---
    offset_val = watchlist.get("_telegram_offset", None)
    updates, new_offset = get_updates(token, offset_val)
    if updates:
        watchlist["_telegram_offset"] = new_offset
        for update in updates:
            process_telegram_update(update, watchlist, responses)

    # --- 2. Poll markets and evaluate alerts ---
    slugs = collect_slugs(watchlist)
    if slugs:
        market_data = fetch_slugs(slugs)
        alerts_to_send = build_alert_batch(watchlist, market_data)

        # Deliver alerts
        deliver_alerts(alerts_to_send, token, watchlist)

    # --- 3. Send command responses ---
    for chat_id, text in responses:
        try:
            send_telegram_dm(text, token, chat_id)
        except Exception as e:
            print(f"Failed to respond to {chat_id}: {e}")

    # --- 4. Save state ---
    # Clean up temp search results before saving
    for user_data in watchlist.get("users", {}).values():
        user_data.pop("_search_results", None)
    save_watchlist(watchlist)

    print(f"Processed {len(updates)} commands, {len(responses)} responses, {len(watchlist.get('users', {}))} users")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_orchestrator.py -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: orchestrator — chain config polling, market fetch, alert eval, delivery"
```

---

### Task 7: GitHub Actions Scheduler

**Files:**
- Create: `.github/workflows/scheduler.yml`

- [ ] **Step 1: Write `.github/workflows/scheduler.yml`**

```yaml
name: Market Watchdog

on:
  schedule:
    - cron: "*/10 * * * *"
  workflow_dispatch:

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Restore watchlist state
        uses: actions/cache/restore@v4
        id: cache-restore
        with:
          path: watchlist.json
          key: watchdog-state-${{ github.run_id }}
          restore-keys: |
            watchdog-state-

      - name: Run orchestrator
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
        run: python scripts/orchestrator.py

      - name: Save watchlist state
        uses: actions/cache/save@v4
        with:
          path: watchlist.json
          key: watchdog-state-${{ github.run_id }}
```

- [ ] **Step 2: Verify workflow syntax**

```bash
# Check file looks correct
cat .github/workflows/scheduler.yml
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/scheduler.yml
git commit -m "feat: GitHub Actions scheduler — 10-min cron with state cache"
```

---

### Task 8: Telegram Bot Token & Final Wiring

**Files:**
- Modify: `scripts/orchestrator.py` (verify imports)
- Create: `.env` (user adds token manually)

- [ ] **Step 1: Add `.env` to `.gitignore` (already done, verify)**

```bash
grep -n ".env" .gitignore
```

Expected: `.env` should appear (line 1 in the file we created in Task 1).

- [ ] **Step 2: Run full test suite**

```bash
python -m pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 3: Add TELEGRAM_BOT_TOKEN as GitHub secret**

```bash
# Manual step — user creates bot via @BotFather and adds secret
echo "1. Create bot via @BotFather on Telegram"
echo "2. Copy bot token"
echo "3. Add to GitHub repo: Settings > Secrets > TELEGRAM_BOT_TOKEN"
```

- [ ] **Step 4: Commit and push**

```bash
git add .
git status
git commit -m "chore: final wiring, test suite verifies"
git push origin main
```

- [ ] **Step 5: Enable GitHub Actions**

The workflow triggers on push to main and on the cron schedule. Verify the first run succeeds at `https://github.com/aw-th33/market-watchdog/actions`.

---

## Post-MVP Checkpoints

After MVP is live and running:

1. **Test with real user**: `/watch 2026 NBA`, verify alerts arrive as DMs
2. **Observe API rate limits**: Gamma API has no documented limits but monitor
3. **Cooldown tuning**: Adjust default 30-min cooldown based on noise level
4. **Error handling**: Telegram API failures, Gamma API timeouts — logged but not crashing
5. **Tier limits**: Add `tier` field per user with market cap checks (Phase 2 monetization)
```

<｜DSML｜parameter name="content" string="true"># Market Watchdog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Standalone Telegram bot that lets users watch any Polymarket market and receive DMs when prob/vol/spread thresholds are breached.

**Architecture:** 4 modules (config_handler, market_poller, alert_evaluator, alert_delivery) chained by orchestrator. GitHub Actions cron every 10 min. State in `watchlist.json` persisted via Actions cache. No Odds API — 100% Gamma API.

**Tech Stack:** Python 3, requests, pytest. Telegram Bot API (polling). Polymarket Gamma API (free/public).

**Repo:** `github.com/aw-th33/market-watchdog` (private, empty)

---

## File Structure

```
market-watchdog/
├── scripts/
│   ├── state.py             # read/save watchlist.json, load .env
│   ├── config_handler.py    # parse /watch, /unwatch, /threshold etc.
│   ├── market_poller.py     # fetch Gamma API for watched slugs
│   ├── alert_evaluator.py   # check thresholds, apply cooldown
│   ├── alert_delivery.py    # send Telegram DM, update last-* fields
│   └── orchestrator.py      # chain: process commands → poll → eval → deliver
├── tests/
│   ├── test_state.py
│   ├── test_config_handler.py
│   ├── test_market_poller.py
│   ├── test_alert_evaluator.py
│   ├── test_alert_delivery.py
│   └── test_orchestrator.py
├── watchlist.json
├── requirements.txt
├── .env.example
├── .gitignore
└── .github/workflows/scheduler.yml
```