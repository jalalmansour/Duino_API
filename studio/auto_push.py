#!/usr/bin/env python3
"""
Duino API — Auto-push script
Run this in the background to watch for file changes and auto-commit+push.

Usage:
    python studio/auto_push.py              # watch & auto-push
    python studio/auto_push.py --once       # commit+push once now and exit
    python studio/auto_push.py --interval 30  # check every 30 seconds
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WATCH_INTERVAL = 60  # seconds


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def has_changes() -> bool:
    r = git("status", "--porcelain")
    return bool(r.stdout.strip())


def commit_and_push(message: str | None = None) -> bool:
    """Stage all, commit, push. Returns True if something was pushed."""
    if not has_changes():
        return False

    # Stage all
    git("add", "-A")

    # Build commit message
    if not message:
        # List changed files for a meaningful auto-commit message
        r = git("diff", "--cached", "--name-only")
        changed = r.stdout.strip().replace("\n", ", ")
        message = f"chore: auto-update [{changed}]"

    # Commit
    git("commit", "-m", message)

    # Push
    try:
        git("push", "origin", "main")
        return True
    except subprocess.CalledProcessError as exc:
        print(f"[auto-push] Push failed: {exc.stderr}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Duino API auto-push watcher")
    parser.add_argument("--once", action="store_true",
                        help="Commit+push once and exit")
    parser.add_argument("--interval", type=int, default=WATCH_INTERVAL,
                        help=f"Check interval in seconds (default: {WATCH_INTERVAL})")
    parser.add_argument("--message", default=None,
                        help="Custom commit message (--once mode)")
    args = parser.parse_args()

    print(f"[auto-push] Repo: {REPO_ROOT}")
    print(f"[auto-push] Remote: {git('remote', 'get-url', 'origin').stdout.strip()}")

    if args.once:
        if commit_and_push(args.message):
            print("[auto-push] ✅ Pushed successfully")
        else:
            print("[auto-push] ℹ️  Nothing to push (working tree clean)")
        return

    print(f"[auto-push] Watching every {args.interval}s — Ctrl+C to stop")
    try:
        while True:
            if has_changes():
                print(f"[auto-push] Changes detected — committing...")
                if commit_and_push():
                    print(f"[auto-push] ✅ Pushed at {time.strftime('%H:%M:%S')}")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n[auto-push] Stopped.")


if __name__ == "__main__":
    main()
