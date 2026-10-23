"""Offline next-wave proposal. No networking, process launches, or lock persistence.

Tiers/cost ranks are operator-supplied heuristics, not model benchmarks/prices.
runtime_worker_slots is total observed worker capacity, not additional free slots.
Use canonical workspaces and concrete relative path prefixes; glob scopes are refused.
"""
import argparse
import json
import math
import posixpath
import sys
from collections import deque
from pathlib import Path

LEVELS = ["low", "medium", "high", "xhigh", "max", "ultra"]
TRANSIENT = {"auth", "network", "permission", "quota", "unsupported_model"}
STATUSES = {"ready", "unknown", "quota_exhausted", "disabled", "unavailable"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def positive_int(value, field):
    require(type(value) is int and value > 0, f"{field}: positive integer required")
    return value


def strings(value, field):
    require(isinstance(value, list) and all(isinstance(x, str) and x for x in value),
            f"{field}: list of nonempty strings required")
    return value


def tier(value):
    require(type(value) is int and 1 <= value <= 3, "tier must be 1, 2, or 3")
    return value


def prefixes(item, key, case_sensitive):
    result = []
    for raw in strings(item.get(key, []), key):
        path = raw.replace("\\", "/")
        require(not any(c in path for c in "*?[]"), "Use concrete prefixes, not globs")
        require(not path.startswith("/") and ":" not in path and ".." not in path.split("/"),
                "Scopes must be relative without parent traversal")
        path = posixpath.normpath(path).rstrip("/")
        result.append(path if case_sensitive else path.casefold())
    return result


def overlap(a, b):
    return a == "." or b == "." or a == b or a.startswith(b + "/") or b.startswith(a + "/")


def conflict(a, b, case_sensitive=False):
    if a.get("session") and a.get("session") == b.get("session"):
        return "session already occupied"
    if set(a.get("locks", [])) & set(b.get("locks", [])):
        return "shared resource occupied"
    wa, wb = a.get("workspace", "main"), b.get("workspace", "main")
    if not case_sensitive:
        wa, wb = wa.casefold(), wb.casefold()
    if wa != wb:
        return None
    ar, aw = prefixes(a, "reads", case_sensitive), prefixes(a, "writes", case_sensitive)
    br, bw = prefixes(b, "reads", case_sensitive), prefixes(b, "writes", case_sensitive)
    if any(overlap(x, y) for x in aw for y in br + bw):
        return "write/read or write/write scope conflict"
    if any(overlap(x, y) for x in ar for y in bw):
        return "read/write scope conflict"
    return None


def validate_resource(item, case_sensitive):
    require(isinstance(item, dict), "resource entry must be an object")
    require(isinstance(item.get("workspace", "main"), str) and item.get("workspace", "main"),
            "workspace must be a nonempty canonical identifier")
    prefixes(item, "reads", case_sensitive)
    prefixes(item, "writes", case_sensitive)
    strings(item.get("locks", []), "locks")
    require(item.get("session") is None or isinstance(item["session"], str), "invalid session")
    require(type(item.get("scope_free", False)) is bool, "scope_free must be boolean")
    require(not item.get("scope_free") or not (item.get("reads") or item.get("writes")),
            "scope_free workers cannot access live files")


def choose_effort(candidate, task, required):
    supported = candidate.get("efforts", [])
    explicit = task.get("effort")
    if explicit is not None:
        return explicit, "explicit supported task setting"
    desired = ["low", "medium", "high"][required - 1]
    if not supported:
        return None, "no exposed effort control; default/inherit, actual unknown"
    target = LEVELS.index(desired)
    # Closest supported level at/below target; otherwise the smallest above it.
    below = [x for x in supported if LEVELS.index(x) <= target]
    selected = max(below, key=LEVELS.index) if below else min(supported, key=LEVELS.index)
    return selected, f"desired {desired}; supported selection {selected}; actual unverified"


def propose(manifest):
    require(isinstance(manifest, dict), "manifest must be an object")
    profile = manifest.get("profile", "balanced")
    require(profile in {"economy", "balanced", "quality"}, "invalid profile")
    cap = min(positive_int(manifest.get("max_workers", 3), "max_workers"),
              positive_int(manifest.get("runtime_worker_slots", 3), "runtime_worker_slots"))
    case_sensitive = manifest.get("case_sensitive", False)
    require(type(case_sensitive) is bool, "case_sensitive must be boolean")
    allowed = set(strings(manifest.get("allowed_engines", []), "allowed_engines"))
    done = set(strings(manifest.get("done", []), "done"))
    tasks = manifest.get("tasks", [])
    active = manifest.get("active", [])
    candidates = manifest.get("candidates", [])
    require(all(isinstance(x, list) for x in [tasks, active, candidates]), "arrays required")
    by_id = {}
    for task in tasks:
        validate_resource(task, case_sensitive)
        tid = task.get("id")
        require(isinstance(tid, str) and tid and tid not in by_id, "unique task IDs required")
        by_id[tid] = task
        tier(task.get("tier", 2))
        require(task.get("risk", "medium") in {"low", "medium", "high"}, "invalid risk")
        mode = task.get("mode")
        require(mode in {"read", "write"}, f"{tid}: mode read/write required")
        require(mode != "read" or not task.get("writes"), f"{tid}: read worker cannot own writes")
        require(mode != "write" or task.get("writes"), f"{tid}: writer needs explicit scopes")
        require(mode != "read" or task.get("reads") or task.get("scope_free") is True,
                f"{tid}: reader needs scopes or explicit scope_free=true")
        require(bool(strings(task.get("acceptance", []), "acceptance")), f"{tid}: acceptance required")
        strings(task.get("depends_on", []), "depends_on")
        strings(task.get("required_capabilities", []), "required_capabilities")
        require(task.get("effort") is None or task["effort"] in LEVELS, "invalid effort")
        require(type(task.get("failed_attempts", 0)) is int and task.get("failed_attempts", 0) >= 0,
                "failed_attempts must be nonnegative integer")
    # Iterative graph validation supports long backlogs without Python recursion limits.
    indegree = {tid: 0 for tid in by_id}
    children = {tid: [] for tid in by_id}
    for tid, task in by_id.items():
        for dep in set(task.get("depends_on", [])):
            require(dep in by_id or dep in done, f"unknown dependency {dep}")
            if dep in by_id:
                indegree[tid] += 1
                children[dep].append(tid)
    ready = deque(tid for tid, count in indegree.items() if count == 0)
    visited_count = 0
    while ready:
        tid = ready.popleft()
        visited_count += 1
        for child in children[tid]:
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
    require(visited_count == len(by_id), "dependency cycle")
    active_ids = set()
    for item in active:
        validate_resource(item, case_sensitive)
        require(isinstance(item.get("id"), str) and item["id"] and item["id"] not in active_ids,
                "active entries need unique IDs")
        require(item["id"] not in done, "active task cannot also be done")
        active_ids.add(item["id"])
    candidate_ids = set()
    for c in candidates:
        require(isinstance(c, dict) and isinstance(c.get("id"), str) and c["id"]
                and c["id"] not in candidate_ids, "unique candidate IDs required")
        candidate_ids.add(c["id"])
        tier(c.get("tier", 2))
        strings(c.get("efforts", []), "efforts")
        require(set(c.get("efforts", [])) <= set(LEVELS), "unsupported effort vocabulary")
        strings(c.get("capabilities", []), "capabilities")
        strings(c.get("allowed_data_classes", []), "allowed_data_classes")
        if c.get("cost_rank") is not None:
            positive_int(c["cost_rank"], "cost_rank")
        require(c.get("status", "unknown") in STATUSES,
                f"{c['id']}: status must be one of {sorted(STATUSES)}")
        require(c.get("pool") is None or (isinstance(c["pool"], str) and c["pool"]),
                f"{c['id']}: pool must be a nonempty string")
    # Routes sharing an account pool share its allowance: one exhausted route blocks the pool.
    exhausted = set(strings(manifest.get("exhausted_pools", []), "exhausted_pools"))
    exhausted |= {c["pool"] for c in candidates
                  if c.get("pool") and c.get("status") == "quota_exhausted"}
    wave, waiting = [], []
    # A running worker with missing scopes is not evidence that the workspace is free.
    occupied = [{**item, "writes": ["."]}
                if not item.get("reads") and not item.get("writes") and not item.get("scope_free")
                else item for item in active]
    for task in tasks:
        tid = task["id"]
        if tid in done or tid in active_ids:
            continue
        reason = None
        if not set(task.get("depends_on", [])) <= done:
            reason = "dependencies not accepted/done"
        elif task.get("failure_kind") in TRANSIENT:
            reason = "resolve access/environment/quota, do not escalate reasoning"
        elif task.get("failed_attempts", 0) >= 2 and not task.get("replanned"):
            reason = "retry limit: coordinator must replan"
        else:
            for other in occupied:
                reason = conflict(task, other, case_sensitive)
                if reason:
                    break
        if reason:
            waiting.append({"task": tid, "reason": reason})
            continue
        if len(occupied) >= cap:
            waiting.append({"task": tid, "reason": "worker capacity exhausted"})
            continue
        required = min(3, max(task.get("tier", 2), 3 if task.get("risk") == "high" else 1)
                       + (1 if task.get("failed_attempts", 0) else 0))
        eligible = []
        for c in candidates:
            if not (c.get("enabled") is True and c.get("authorized") is True
                    and c.get("status") == "ready" and c.get("evidence")
                    and isinstance(c.get("model"), str) and c["model"]
                    and c.get("engine") in allowed and c.get("tier", 2) >= required):
                continue
            if c.get("pool") in exhausted:
                continue
            caps = set(task.get("required_capabilities", [])) | {task["mode"]}
            if not caps <= set(c.get("capabilities", [])):
                continue
            if task.get("data_class", "project-private") not in c.get("allowed_data_classes", []):
                continue
            if task.get("required_engine") and c["engine"] != task["required_engine"]:
                continue
            if task.get("required_model") and c["model"] != task["required_model"]:
                continue
            if task.get("effort") and task["effort"] not in c.get("efforts", []):
                continue
            eligible.append(c)
        if not eligible:
            waiting.append({"task": tid, "reason": "no eligible authorized observed route"})
            continue

        def rank(c):
            cost = c.get("cost_rank") if c.get("cost_rank") is not None else math.inf
            depth = c.get("tier", 2)
            preference = 0 if c.get("engine") == task.get("preferred_engine") else 1
            if profile == "economy":
                return cost, depth, preference, c["id"]
            if profile == "quality" and required >= 2:
                return -depth, preference, cost, c["id"]
            return depth, preference, cost, c["id"]

        selected = min(eligible, key=rank)
        effort, effort_note = choose_effort(selected, task, required)
        wave.append({"task": tid, "candidate": selected["id"], "engine": selected["engine"],
                     "requested_model": selected["model"], "requested_effort": effort,
                     "actual_model": None, "actual_effort": None,
                     "reason": f"{profile}; required role tier {required}; eligible observed pool",
                     "effort_note": effort_note})
        occupied.append(task)
    return {"execution": "proposal_only", "worker_capacity": cap, "active_workers": len(active),
            "exhausted_pools": sorted(exhausted), "ready_wave": wave, "waiting": waiting,
            "warning": "No calls, durable locks or budget enforcement. Recheck live state before dispatch."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    # Task titles may be in any language; a cp1251/cp437 console must not crash the output.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    try:
        result = propose(json.loads(args.manifest.read_text(encoding="utf-8-sig")))
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
