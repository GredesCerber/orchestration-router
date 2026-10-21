"""Read the last Codex plan-usage values from local session logs. Read-only, no model run.

Codex CLI/app session files ($CODEX_HOME/sessions/**/rollout-*.jsonl) contain token_count
events with rate_limits.primary/secondary {used_percent, window_minutes, resets_at}.
This is an observed local format (codex-cli 0.156), not a documented API: if it changes,
the script reports "not found" rather than guessing. Prefer a native usage tool when the
host has one. Values are as of the newest event, so check `checked_at` for staleness.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def newest_sessions(home, limit=5):
    root = home / "sessions"
    if not root.is_dir():
        return []
    files = [p for p in root.rglob("rollout-*.jsonl") if p.is_file()]
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)[:limit]


def last_rate_limits(path):
    found = None
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if '"rate_limits"' not in line:
                continue
            try:
                event = json.loads(line)
            except ValueError:
                continue
            stack = [event]
            while stack:
                node = stack.pop()
                if isinstance(node, dict):
                    if isinstance(node.get("rate_limits"), dict):
                        found = (event.get("timestamp"), node["rate_limits"])
                        break
                    stack.extend(node.values())
                elif isinstance(node, list):
                    stack.extend(node)
    return found


def window(label, w):
    used = w.get("used_percent")
    resets = w.get("resets_at")
    return {"label": label, "window_minutes": w.get("window_minutes"), "used_percent": used,
            "remaining_percent": None if used is None else max(0.0, min(100.0, 100.0 - used)),
            "resets_at": None if resets is None
            else datetime.fromtimestamp(resets, timezone.utc).isoformat()}


def main():
    home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    for path in newest_sessions(home):
        hit = last_rate_limits(path)
        if not hit:
            continue
        stamp, limits = hit
        windows = [window(name, limits[name]) for name in ("primary", "secondary")
                   if isinstance(limits.get(name), dict)]
        credits = limits.get("credits") or {}
        result = {"pool": "codex-subscription", "source": "codex session log (observed format)",
                  "checked_at": stamp or datetime.fromtimestamp(
                      path.stat().st_mtime, timezone.utc).isoformat(),
                  "freshness": "last-known", "windows": windows,
                  "extra_credits": {"has_credits": credits.get("has_credits")},
                  "blocked": None}
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 0
    print(json.dumps({"pool": "codex-subscription", "error": "no rate_limits found in recent sessions"}))
    return 1


if __name__ == "__main__":
    sys.exit(main())
