# Offline next-wave planner

Use `scripts/plan_wave.py` for repetitive checks over a prepared backlog. It outputs JSON to stdout, never edits the manifest, calls a model, reads environment credentials, starts processes or persists locks. Run with any Python 3.10+ interpreter; no third-party modules are needed.

```text
python -B <skill-dir>/scripts/plan_wave.py <project-task-manifest.json>
python -B <skill-dir>/scripts/test_plan_wave.py
```

## Input contract

The coordinator owns this manifest. Use live canonical workspaces and an accurate list of all active descendants. Input is not automatically a trustworthy account inventory.

| Field | Meaning |
|---|---|
| `profile` | economy, balanced (default), quality |
| `max_workers` | total project worker cap; excludes the coordinating root |
| `runtime_worker_slots` | observed total capacity for workers, **not free slots**; count others occupying it in active |
| `allowed_engines` | explicit selected executor IDs, e.g. codex-native and claude-code |
| `done` | accepted dependency/task IDs; dispatch or a partial report is not acceptance |
| `active` | every active worker/descendant, its ID, workspace, reads, writes, resource locks and existing session |
| `candidates` | observed authorized model routes, described below |
| `tasks` | ordered queued packets; coordinator orders by priority/dependencies |
| `case_sensitive` | false by default for conservative Windows path matching |
| `exhausted_pools` | optional list of quota pools confirmed exhausted by the current snapshot |

`done` and `active` can be copied from the ledger ([ledger.example.json](../assets/ledger.example.json)).

Candidate fields: unique `id`, `engine`, observed nonempty `model` ID/alias, boolean `enabled` and `authorized`, `status: ready`, nonempty `evidence`, role `tier` 1–3, supported `efforts` list, `capabilities` list, `allowed_data_classes`. Missing access/evidence keeps a candidate ineligible. Empty efforts means no exposed override; requested effort is null. `cost_rank` is an optional positive integer expressing relative preference, not pricing.

`status` must be one of `ready`, `unknown`, `quota_exhausted`, `disabled`, `unavailable`; anything else rejects the manifest, so a typo cannot silently disable a route. Optional `pool` names the account allowance a route draws from (for example `claude-subscription`).

Apply current quota observations before planning, following [usage-limits.md](usage-limits.md). Either set a confirmed exhausted route's status to `quota_exhausted` or list its pool in the top-level `exhausted_pools`. Every candidate with the same `pool` then becomes ineligible, and the output repeats the blocked pools. The helper itself does not query live usage or infer quota from token costs.

Role tiers are supplied by the coordinator: 1 bounded/light, 2 ordinary, 3 deep/complex. They are not inferred from a brand name or benchmarked by this script. The script cannot determine whether a guessed role is actually adequate.

Task fields: unique `id`, `mode: read|write`, canonical `workspace`, concrete relative-prefix `reads`/`writes`, `locks`, `depends_on`, nonempty `acceptance`, `tier`, `risk: low|medium|high`, `required_capabilities`, `data_class`. A writer must own scopes; a reader cannot list writes and needs a nonempty read scope. Modes add a required read/write capability automatically.

For work using only the supplied packet or immutable context with no live-file access, explicitly set `scope_free: true` and leave reads/writes empty. Omitting scopes is not the same as declaring no access. An active worker without known scopes or scope_free reserves its entire workspace as an unknown writer until reconciled.

Optional task constraints:
- `required_engine`/`required_model`: hard filters; no silent substitution.
- `preferred_engine`: soft tie-break; economy compares cost and adequate depth first. For mandatory executor selection use required_engine.
- `effort`: explicit required supported level; unsupported candidates are excluded.
- `session`: existing session identifier; any identical occupied session waits, even across workspaces.
- `failed_attempts`: one substantive failure raises requested role depth one tier; two require coordinator replanning. `replanned: true` means a documented new plan, not an automatic bypass.
- `failure_kind`: auth/network/permission/quota/unsupported_model waits for environment resolution.

The helper does not model reset deadlines or the user's allocation preference (see SKILL.md). To route chosen packets to a provider under that preference, set `required_engine` on those packets; a soft `preferred_engine` can lose to cost ranking in economy mode.

Paths cannot contain globs, absolute prefixes, drive letters or `..`. A directory prefix conflicts with descendants. Use `.` for the whole workspace. Canonicalize actual workspace/path identities (including aliases/symlinks) before calling: the helper cannot discover them. Named locks such as `db:pilot-copy`, `port:8080` or `build:release` apply across workspaces. All named locks are exclusive.

## Output and limits

`ready_wave` contains requested model/effort and routing rationale; actual values remain null until verified by the executor. `waiting` records why other tasks must wait. Dependencies must be in done, so a task is not launched alongside its prerequisite. Invalid manifests fail with exit code 2.

The wave is greedy in task order. It is not a globally optimal scheduler or a semantic quality estimator. Policy requests low/medium/high by required tier; only supported values are emitted. Explicit task effort is honored exactly or the route waits. If an automatic desired level cannot be matched, the note states the supported selection; the coordinator must judge adequacy.

Only executable packets belong in tasks: a missing acceptance/scope rejects the manifest. Keep unclear work in the coordinator's unrefined backlog until it has an execution contract.

Reconcile active processes, reserve ownership, confirm data/cost authorization and then dispatch with actual tools. The helper does not enforce OS permissions, process exclusivity, current quotas, provider settings, approval requirements or aggregate spend. Do not present a successful proposal as completed work.
