"""Optional Claude Code status line that also saves a plan-usage snapshot for coordinators.

Claude Code pipes session JSON to the status line command. For Pro/Max accounts, after the
first response, it includes rate_limits.five_hour / seven_day with used_percentage and
resets_at (https://code.claude.com/docs/en/statusline). This script prints a short line and
writes only those numbers plus a timestamp to the snapshot file. No tokens, account IDs or
prompts are stored. Installing it edits ~/.claude/settings.json: do it only with the user's OK.

  "statusLine": {"type": "command", "command": "python -B <skill-dir>/scripts/claude_usage_statusline.py"}

Snapshot path: $CLAUDE_USAGE_SNAPSHOT or ~/.claude/usage-snapshot.json
"""
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

WINDOWS = (("five_hour", "5h"), ("seven_day", "7d"))


def snapshot(data):
    limits = data.get("rate_limits") or {}
    windows = []
    for key, label in WINDOWS:
        w = limits.get(key)
        if not isinstance(w, dict):
            continue
        used = w.get("used_percentage")
        resets = w.get("resets_at")
        windows.append({
            "label": label,
            "used_percent": used,
            "remaining_percent": None if used is None else max(0.0, min(100.0, 100.0 - used)),
            "resets_at": None if resets is None
            else datetime.fromtimestamp(resets, timezone.utc).isoformat(),
        })
    return {"pool": "claude-subscription", "source": "claude statusline rate_limits",
            "checked_at": datetime.now(timezone.utc).isoformat(), "freshness": "current",
            "windows": windows, "blocked": None}


def save(snap, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".usage-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def main():
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}")
    except ValueError:
        data = {}
    snap = snapshot(data)
    if snap["windows"]:
        target = Path(os.environ.get("CLAUDE_USAGE_SNAPSHOT",
                                     Path.home() / ".claude" / "usage-snapshot.json"))
        try:
            save(snap, target)
        except OSError:
            pass  # A status line must never fail the session.
    model = (data.get("model") or {}).get("display_name", "")
    parts = [model] if model else []
    parts += [f"{w['label']} {w['used_percent']:.0f}%" for w in snap["windows"]
              if w["used_percent"] is not None]
    print(" | ".join(parts) or "usage n/a")  # ASCII: Windows consoles may not be UTF-8


if __name__ == "__main__":
    main()
