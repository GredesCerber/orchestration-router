"""Local, read-only executor discovery. Never starts a model run, reads no credentials.

Prints a JSON skeleton for the project inventory: which agent CLIs are on PATH, their
versions, and capability flags that are visible without authentication. Every candidate
comes out enabled=false/authorized=false: the coordinator (or the user) confirms access.
"""
import json
import os
import shutil
import subprocess
import sys

# Feature flags in `codex features list` that matter for routing.
CODEX_FEATURES = {"image_generation", "apps", "browser_use", "computer_use",
                  "multi_agent", "memories", "goals", "hooks"}
# Only names are inspected, never values.
HOST_MARKERS = {"claude-code": ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"),
                "codex": ("CODEX_THREAD_ID", "CODEX_SANDBOX", "CODEX_HOME")}


def run(argv, timeout=20):
    try:
        out = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=timeout)
        return out.returncode, (out.stdout or "") + (out.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)


def first_line(text):
    return next((line.strip() for line in text.splitlines() if line.strip()), "")


def codex_features(exe):
    code, text = run([exe, "features", "list"])
    if code != 0:
        return {}
    flags = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] in CODEX_FEATURES:
            flags[parts[0]] = parts[-1] == "true"
    return flags


def candidate(cid, engine, exe, version, capabilities, extra=None):
    item = {"id": cid, "engine": engine, "executable": exe, "version": version,
            "model": None, "enabled": False, "authorized": False, "status": "unknown",
            "evidence": f"discover.py: {version}" if version else None,
            "tier": 2, "pool": None, "cost_rank": None,
            "capabilities": capabilities, "efforts": [], "allowed_data_classes": []}
    item.update(extra or {})
    return item


def discover():
    hosts = [name for name, markers in HOST_MARKERS.items()
             if any(m in os.environ for m in markers)]
    result = {"execution": "discovery_only",
              "host_hint": hosts or ["unknown"],
              "host_note": "Hint from environment variable names; a child process inherits its "
                           "parent's markers. Trust the agent's own knowledge of its harness.",
              "candidates": [], "not_found": []}

    claude = shutil.which("claude")
    if claude:
        code, text = run([claude, "--version"])
        result["candidates"].append(candidate(
            "claude-cli", "claude-code", claude, first_line(text) if code == 0 else None,
            ["code", "read", "write"],
            {"pool": "claude-subscription",
             "efforts_hint": ["low", "medium", "high", "xhigh", "max"],
             "launch": "references/executors.md#claude-code"}))
    else:
        result["not_found"].append("claude")

    codex = shutil.which("codex")
    if codex:
        code, text = run([codex, "--version"])
        flags = codex_features(codex)
        caps = ["code", "read", "write"]
        if flags.get("image_generation"):
            caps.append("image_generation")
        if flags.get("apps"):
            caps.append("apps")
        if flags.get("browser_use"):
            caps.append("browser")
        if flags.get("computer_use"):
            caps.append("computer_use")
        result["candidates"].append(candidate(
            "codex-cli", "codex-cli", codex, first_line(text) if code == 0 else None, caps,
            {"pool": "codex-subscription", "feature_flags": flags,
             "launch": "references/executors.md#codex-cli"}))
    else:
        result["not_found"].append("codex")

    for name in ("gemini", "opencode", "aider"):
        exe = shutil.which(name)
        if exe:
            code, text = run([exe, "--version"])
            result["candidates"].append(candidate(
                f"{name}-cli", name, exe, first_line(text) if code == 0 else None,
                ["code", "read", "write"],
                {"note": "No adapter in this skill; read its --help before use."}))
    result["next"] = ("Fill model/efforts/allowed_data_classes from the user's choices, set "
                      "enabled/authorized only for confirmed routes, add native subagents of the "
                      "current host, then check usage (references/usage-limits.md).")
    return result


if __name__ == "__main__":
    json.dump(discover(), sys.stdout, ensure_ascii=False, indent=2)
    print()
