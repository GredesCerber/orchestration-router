"""Start, inspect and collect agent CLI workers the same way on Windows, macOS and Linux.

  launch.py start  --engine claude|codex --role read|write --task-id ID --run-dir DIR
                   --cwd REPO --packet FILE [--model M] [--effort E] [--allow-tool T ...]
                   [--worktree] [--add-dir D ...] [--dry-run]
  launch.py status --run-dir DIR
  launch.py wait   --run-dir DIR [--timeout SECONDS] [--interval SECONDS]

Arguments go to the child as a list (no shell, no quoting rules per OS). The packet is fed
on stdin from a UTF-8 file. Logs and run.json land in --run-dir. Permission-bypass flags
cannot be requested. This script starts a model run only on `start` without --dry-run.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROLES = {"read", "write"}
BATCH_UNSAFE = set('&|<>^%!"')  # cmd.exe metacharacters, relevant only for .cmd/.bat shims


def claude_argv(exe, a):
    argv = [exe, "-p", "--output-format", "stream-json", "--verbose", "--name", a.task_id]
    if a.model:
        argv += ["--model", a.model]
    if a.effort:
        argv += ["--effort", a.effort]
    if a.role == "read":
        argv += ["--permission-mode", "plan"]
    else:
        argv += ["--permission-mode", "acceptEdits"]
        if a.allow_tool:
            argv += ["--allowedTools", *a.allow_tool]
    if a.worktree:
        argv += ["--worktree", a.task_id]
    for d in a.add_dir:
        argv += ["--add-dir", d]
    return argv


def codex_argv(exe, a, run_dir):
    argv = [exe, "exec", "--json", "-o", str(run_dir / "last.txt"), "-C", a.cwd,
            "-s", "read-only" if a.role == "read" else "workspace-write"]
    if a.model:
        argv += ["-m", a.model]
    if a.effort:
        argv += ["-c", f'model_reasoning_effort="{a.effort}"']
    if a.worktree:
        argv += ["--worktree"]
    if not (Path(a.cwd) / ".git").exists():
        argv += ["--skip-git-repo-check"]
    for d in a.add_dir:
        argv += ["--add-dir", d]
    return argv + ["-"]  # read the prompt from stdin


def build(a, run_dir):
    exe = shutil.which(a.engine)
    if not exe:
        raise SystemExit(f"{a.engine} not found on PATH")
    argv = claude_argv(exe, a) if a.engine == "claude" else codex_argv(exe, a, run_dir)
    if any(x in arg.lower() for arg in argv for x in ("dangerously", "bypass")):
        raise SystemExit("refusing permission-bypass arguments")
    if exe.lower().endswith((".cmd", ".bat")) and any(set(arg) & BATCH_UNSAFE for arg in argv[1:]):
        raise SystemExit("batch-file shim: arguments contain cmd.exe metacharacters; "
                         "use the native executable or simplify the arguments")
    return argv


def alive(pid):
    if os.name == "nt":
        import ctypes
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def start(a):
    run_dir = Path(a.run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    packet = Path(a.packet).resolve()
    packet.read_text(encoding="utf-8")  # fail early on a missing or non-UTF-8 packet
    argv = build(a, run_dir)
    record = {"task_id": a.task_id, "engine": a.engine, "role": a.role, "cwd": a.cwd,
              "argv": argv, "packet": str(packet), "pid": None,
              "started_at": datetime.now(timezone.utc).isoformat()}
    if a.dry_run:
        print(json.dumps({**record, "dry_run": True}, ensure_ascii=False, indent=2))
        return 0
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    else:
        kwargs["start_new_session"] = True
    with packet.open("rb") as stdin, (run_dir / "events.jsonl").open("wb") as out, \
            (run_dir / "stderr.txt").open("wb") as err:
        proc = subprocess.Popen(argv, cwd=a.cwd, stdin=stdin, stdout=out, stderr=err, **kwargs)
    record["pid"] = proc.pid
    (run_dir / "run.json").write_text(json.dumps(record, ensure_ascii=False, indent=2),
                                      encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


def summarize(engine, events_path, run_dir):
    info = {"session_id": None, "final_text": None, "usage": None, "errors": []}
    if events_path.exists():
        for line in events_path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                e = json.loads(line)
            except ValueError:
                continue
            kind = e.get("type")
            if engine == "claude":
                if kind == "result":
                    info.update(session_id=e.get("session_id"), final_text=e.get("result"),
                                usage=e.get("usage"))
                    if e.get("is_error"):
                        info["errors"].append(e.get("subtype"))
            else:
                if kind == "thread.started":
                    info["session_id"] = e.get("thread_id")
                elif kind == "turn.completed":
                    info["usage"] = e.get("usage")
                elif kind == "item.completed" and (e.get("item") or {}).get("type") == "agent_message":
                    info["final_text"] = e["item"].get("text")
                elif kind in ("error", "turn.failed"):
                    info["errors"].append(e.get("message") or e.get("error"))
    last = run_dir / "last.txt"
    if engine == "codex" and last.exists():
        info["final_text"] = last.read_text(encoding="utf-8", errors="replace")
    if engine == "codex" and info["session_id"]:
        home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
        images = home / "generated_images" / info["session_id"]
        info["generated_images"] = sorted(str(p) for p in images.glob("*")) if images.is_dir() else []
    return info


def collect(run_dir):
    record = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    running = bool(record.get("pid")) and alive(record["pid"])
    result = {"task_id": record["task_id"], "pid": record.get("pid"), "running": running,
              **summarize(record["engine"], run_dir / "events.jsonl", run_dir)}
    err = run_dir / "stderr.txt"
    if err.exists():
        result["stderr_tail"] = err.read_text(encoding="utf-8", errors="replace")[-1500:]
    return result


def status(a):
    print(json.dumps(collect(Path(a.run_dir).resolve()), ensure_ascii=False, indent=2))
    return 0


def wait(a):
    """Block until the worker exits or --timeout passes; exit 0 when done, 3 on timeout."""
    run_dir = Path(a.run_dir).resolve()
    deadline = time.monotonic() + a.timeout
    result = collect(run_dir)
    while result["running"] and time.monotonic() < deadline:
        time.sleep(min(a.interval, max(0.0, deadline - time.monotonic())))
        result = collect(run_dir)
    result["timed_out"] = result["running"]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 3 if result["timed_out"] else 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start")
    s.add_argument("--engine", choices=["claude", "codex"], required=True)
    s.add_argument("--role", choices=sorted(ROLES), required=True)
    s.add_argument("--task-id", required=True)
    s.add_argument("--run-dir", required=True)
    s.add_argument("--cwd", required=True)
    s.add_argument("--packet", required=True)
    s.add_argument("--model")
    s.add_argument("--effort")
    s.add_argument("--allow-tool", action="append", default=[],
                   help='claude write role only, e.g. "Bash(npm test:*)"')
    s.add_argument("--add-dir", action="append", default=[])
    s.add_argument("--worktree", action="store_true")
    s.add_argument("--dry-run", action="store_true")
    st = sub.add_parser("status")
    st.add_argument("--run-dir", required=True)
    w = sub.add_parser("wait")
    w.add_argument("--run-dir", required=True)
    w.add_argument("--timeout", type=float, default=3600, help="seconds (default 3600)")
    w.add_argument("--interval", type=float, default=20, help="seconds between checks (default 20)")
    a = p.parse_args(argv)
    # Workers answer in any language; a cp1251/cp437 console must not crash the report.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    return {"start": start, "status": status, "wait": wait}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
