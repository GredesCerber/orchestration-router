---
name: orchestration-router
description: Coordinate substantial project work across whatever agents are available — native subagents, Claude Code CLI, Codex CLI, user-authorized APIs — from any host (Codex, Claude Code or another harness). Discover executors, route by capability (e.g. image generation in Codex), select models and effort, check remaining usage, schedule independent tasks, preserve file/session ownership, integrate verified results. Use for explicit orchestration, multi-model routing, delegating to Claude or Codex, or a large backlog (also in Russian: оркестрация, распредели работу, субагенты, отдай Claude, отдай Codex, лимиты, роутинг моделей); keep small dependent tasks in the main agent.
---

# Orchestration Router

Act as one accountable coordinator. Finish the user's deliverable; do not optimize for agent count. This skill is an operational router, not an API gateway: its scripts make no model calls and hold no locks. It is host-neutral: whichever agent loaded it is the coordinator, and every other agent CLI is an executor.

## Precedence

1. The user's current instruction.
2. Project rules (AGENTS.md, a project orchestration file, the coordination checkpoint). Where they set worker counts, model tables, zones or templates, they win over this skill. Do not copy their model table here or create a second coordination system beside theirs.
3. This skill.

Selecting a backend grants it no access to secrets or personal data. Publication, repository visibility, uncertain deletion, spending, legal submission and private-data disclosure keep their own authorization requirements. Routine reversible work inside the request can proceed.

## 1. Restore state

Read project instructions, Git status, the existing ledger/checkpoint, active workers and processes, and who owns files, builds, ports, browsers and databases. Define observable acceptance criteria and the next complete stage. When new messages steer the work, keep the objective.

## 2. Build the pool

Read [executors.md](references/executors.md) before discovering or launching an executor.

- Identify yourself (host and model) from your own knowledge. Run `python -B <skill-dir>/scripts/discover.py` for agent CLIs on PATH and their visible capabilities, then add your native spawn tools. Read `--help` of anything you will launch. Do not start a paid run, install clients, change global settings or buy credits as discovery.
- Route capability-bound packets (image generation, a plugin or app, a browser) to the executor that has the tool, then pick the model inside it.
- Ask which backends to use only if it changes execution; reuse earlier explicit choices.
- Keep a project-local inventory: executor, model ID/alias, availability evidence and date, supported efforts, tools, data boundary, quota pool. Unknown is neither unavailable nor unlimited.
- Route only inside the selected pool. Never silently add a paid API, substitute a mandated model, or call a GPT worker Claude.

## 3. Check usage

Read [usage-limits.md](references/usage-limits.md) before the first quota-aware dispatch. Take a read-only snapshot at stage start, before a large wave or provider switch, and after a limit error or a reported reset; reuse it in between. Show one compact line: pool, remaining per window, reset time, freshness. Unknown stays unknown.

Remove confirmed exhausted pools from routing. On low capacity, reduce fan-out before lowering required depth.

**Allocation preference.** An instruction such as "give Claude more work, its week resets Thursday" applies immediately and persists until superseded. Give that subscription valuable complete stages at the right tier (implementation included, not only reviews). Record the preference and its evidence in the checkpoint. Do not invent tasks or duplicate checks to burn quota.

## 4. Route each packet

Decide separately, using [routing.md](references/routing.md):

1. **Workflow:** do it directly, fan out, chain, or implement-then-review. Keep coupled steps together.
2. **Eligibility:** data destination, tools, model access, user constraints, workspace.
3. **Model:** classify the packet's own difficulty, not the project's. Discovery, search and metadata go to a lightweight model; ambiguous design or consequential review to a strong one.
4. **Effort:** low for clear bounded work, medium for ordinary implementation, high for ambiguous debugging or consequential review. Higher levels only for a named remaining difficulty.
5. **Evidence:** record requested and reported actual model/effort separately.

Environment errors (auth, network, permission, unsupported model) need fixes, not more reasoning.

## 5. Schedule

- Use a dependency graph; batch small similar tasks.
- Default cap: 3 concurrent workers, counting Claude CLI runs and all descendants, unless project rules or the runtime set another. Expand only for ready independent work with resources and quota.
- Reserve paths, shared databases, build outputs, ports and sessions before launch. Readers may overlap; a writer is exclusive on its resource. Worktrees isolate source, not external resources.
- One coordinator writes the ledger and integrates. Never resume one Claude session concurrently or use "continue latest".
- Workers do not delegate unless given an explicit sublimit inside the same cap.

For a large backlog, run the offline planner ([planner.md](references/planner.md)):

```text
python -B <skill-dir>/scripts/plan_wave.py <manifest.json>
```

It proposes the next wave only. Recheck live state before dispatch.

## 6. Delegate

Fill [packet.md](assets/packet.md) for every delegated task. For a cohesive substantial stage, give one capable executor the whole loop (inspect, implement, build/test, repair) with the tools it needs; keep reviewers read-only. Send compact context, not a chat fork. Do not tell a reviewer the desired conclusion.

Require the return in [handoff.md](assets/handoff.md) form.

**Stall control.** If a worker shows no new evidence for 10–15 minutes, or drifts into side work, inspect its log and diff, then narrow the task. A timeout does not prove the child stopped: confirm the process ended before reassigning.

## 7. Accept and integrate

Inspect artifacts, not reports. Check write scope against the packet (`git diff --name-only`), then run proportionate checks; test the integrated result, because isolated passes do not prove the combined build. A partial or usage-limited report is not done. Stage explicit paths; follow project review policy; never auto-publish or bypass branch protection.

## 8. Ledger and recovery

Keep the ledger in the project's checkpoint location, shaped like [ledger.example.json](assets/ledger.example.json). States: queued → reserved → running → review → done, plus blocked and cancelled. Dispatch is not done.

One evidence-informed retry after a reasoning failure; then decompose, move to a stronger eligible route, or report a specific blocker. On a rate limit, stop spawning on that pool, preserve work, continue independent tasks elsewhere.

Report progress briefly in the user's language. Finish with deliverables, checks actually performed and limitations. Create no recurring runs, accounts or background services unless asked.
