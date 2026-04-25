import subprocess, sys, os, time, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(BASE_DIR, "scripts")


def run_step(name, script):
    print("=" * 55)
    print("STEP: {}".format(name))
    print("=" * 55)
    t0 = time.time()
    result = subprocess.run(
        [sys.executable, os.path.join(SCRIPTS, script)],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = time.time() - t0
    print(result.stdout)
    if result.stderr.strip():
        print("STDERR:", result.stderr[:500])
    if result.returncode != 0:
        print("FAILED with code {} after {:.1f}s".format(result.returncode, elapsed))
        return False
    print("OK ({:.1f}s)".format(elapsed))
    return True


def main():
    print("Apex Signal Orchestrator")
    print()

    steps = [
        ("Signal engine", "signal_engine.py"),
        ("Alert formatter", "alert_formatter.py"),
        ("Telegram post", "telegram_bot.py"),
        ("Twitter post", "twitter_bot.py"),
    ]

    all_ok = True
    for name, script in steps:
        if not run_step(name, script):
            all_ok = False
            break

    print()
    if all_ok:
        print("Pipeline complete.")
    else:
        print("Pipeline stopped due to error.")
        sys.exit(1)


if __name__ == "__main__":
    main()
