# Executor adapters

Start with `python -B <skill-dir>/scripts/discover.py`: it lists agent CLIs on PATH, versions and visible capability flags without starting a model or reading credentials. Everything it returns is unconfirmed until the user's choices and a first run say otherwise.

The same adapters work from any host. Codex can drive Claude Code; Claude Code can drive Codex; another harness can drive both. The coordinator is whoever loaded this skill.

## Native subagents (current host)

Use the host's actual spawn tool, model/effort options and concurrency limits. Omitted settings can inherit the parent. Some hosts restrict overrides on full-history forks; prefer a compact packet when choosing the worker model. Do not change global config to work around missing per-worker control.

Read-only is a tool boundary, not a worker name. Children may not share the parent's tools, sign-ins or skills: pass exact paths, instructions and context.

### Claude Code `Agent` tool (observed 2026-10-21, cloud session)

- Per call: `model` alias (`haiku`, `sonnet`, `opus`), `effort`, `run_in_background`, optional `isolation: "worktree"`. A regular (non-fork) child starts without the parent's conversation: write the packet to a file and pass its path, or inline it.
- Exception: `subagent_type: "fork"` inherits the whole parent conversation and runs on the parent's model; a `model` override is ignored. Do not use a fork when the packet sets the model or limits what context the worker may see.
- `isolation: "worktree"` may create the worktree from the repository's default branch, not from the parent's `HEAD`. When the packet's base revision is another branch or commit, the packet must tell the worker to check out that revision and confirm `git rev-parse HEAD` before work; otherwise do not isolate.
- Completion arrives as a notification with the child's final text. The runtime does not report which model actually served the child: record `actual.model` as unknown. A child's own claim about its model is self-reported, not evidence.
- Without `isolation: "worktree"` the child shares the parent's working tree and checked-out branch. Until it returns, the coordinator must not switch branches, edit, build or run tests in that checkout; do independent work in another clone or directory.
- In a cloud container `discover.py` may also find a `claude` CLI. It is unauthenticated or bills the same subscription pool, so prefer the native tool there instead of probing the CLI.

## Route by capability first

Some tools exist in only one executor. Send the packet where the tool is, then pick the model inside that executor:

| Need | Typical owner |
|---|---|
| Raster image generation/editing | Codex (`image_gen` built-in, `imagegen` system skill) |
| Codex apps/plugins and their skills (documents, slides, connectors the user enabled in Codex) | Codex |
| Claude Code skills, subagents, hooks, MCP servers configured for Claude | Claude Code |
| Browser or desktop control | whichever host has it connected; headless CLI runs usually do not |

A feature flag or an installed plugin proves the tool exists, not that it works headless or that its account is connected. The first use of a capability through a CLI is a small probe; record the result in the inventory. An app that needs sign-in or consent cannot get it in a background run: return a blocker instead.

## Launching a CLI worker (any OS)

Use `scripts/launch.py`. It passes arguments as a list (no shell quoting, same on Windows, macOS and Linux), feeds the packet on stdin from a UTF-8 file, detaches the child, and writes `run.json`, `events.jsonl` and `stderr.txt` into the run folder. It cannot emit permission-bypass flags.

```text
python -B <skill-dir>/scripts/launch.py start --engine claude|codex --role read|write     --task-id <id> --run-dir <project>/work/orchestration/<id> --cwd <repo>     --packet <run-dir>/packet.txt [--model <m>] [--effort <e>]     [--allow-tool "Bash(npm test:*)"] [--worktree] [--add-dir <dir>] [--dry-run]
python -B <skill-dir>/scripts/launch.py status --run-dir <run-dir>
python -B <skill-dir>/scripts/launch.py wait --run-dir <run-dir> [--timeout 3600] [--interval 20]
```

`start` prints the PID: record it in the ledger before anything else. `status` reports whether the process is alive, the session/thread ID, final text, usage, errors, the stderr tail and, for Codex, files in its `generated_images/<thread_id>/` folder. `wait` blocks until the worker exits (exit code 0) or the timeout passes (exit code 3, `"timed_out": true`) and then prints the same report: run it as one background command instead of a hand-written shell polling loop. Use `--dry-run` to see the exact command line.

Output is always UTF-8. Do not grep the report for `"running": false` in a shell loop: when the report could not be printed, such a loop never ends and the next step never starts. Use `wait`, or parse the JSON.

Verified 2026-10-21 on Windows (PowerShell host, Python 3): one tiny read-only run each of `claude` (haiku, low) and `codex` (lightweight model, low) started, finished and returned their answer and session IDs through `status`. macOS/Linux use the same code path (`start_new_session`) but were not run.

- Poll with bounded waits: `status`, plus `git diff --name-only` in the worker's workspace.
- Never put untrusted text into arguments; it belongs in the packet file.
- A child inherits the parent's environment. Do not put secrets in the packet.
- A timeout does not prove the child exited: `status` must show `running: false` before retry or replacement. Never kill unrelated or user processes.
- If you launch by hand instead, pass arguments as an array through your language's process API, not through a shell string. (PowerShell's `Start-Process -ArgumentList` splits elements on spaces.)

## Claude Code

Flags from `claude --help` of 2.1.296; recheck on the installed version.

Installation is not authentication or quota. Claude Code in print mode (`-p`) is a full agent: give an implementation lead the tools its stage needs, keep reviewers read-only.

**Permissions decide whether a print-mode lead can work at all.** Nobody answers prompts in `-p`, so anything that would prompt is denied. Set the mode explicitly:

| Role | Flags |
|---|---|
| Reviewer / researcher | `--permission-mode plan` |
| Implementer in its scope | `--permission-mode acceptEdits --allowedTools "Bash(npm test:*) Bash(git diff:*) Bash(git status:*)"` (the project's real build/test commands) |
| Isolated writer | add `--worktree <task-id>` when worktrees are allowed and no shared runtime folder is involved |

`launch.py` builds: `-p --output-format stream-json --verbose --name <task-id> --model <alias> --effort <level>` plus the role flags above. (`--json-schema '<schema>'` can enforce the handoff fields; `launch.py` does not add it.) The final `result` event holds `session_id`, usage and the final text.

- Never `--dangerously-skip-permissions` / `bypassPermissions`. `--add-dir` only for directories the packet owns.
- Resume only by recorded ID (`--resume <session-id>`), never concurrently, never "latest".
- Print mode loads project configuration (CLAUDE.md, settings, hooks): use a trusted cwd.
- Model resolution: aliases are not exact versions; `CLAUDE_CODE_SUBAGENT_MODEL`, `CLAUDE_CODE_EFFORT_LEVEL` and managed settings can override requests. Do not change them globally. Supported effort is model-specific.
- Nested workers: give an explicit allowance and count them in the project cap; a prompt cap is advisory. `--max-budget-usd` bounds API spend only, not subscription quota.

## Codex CLI

Flags from `codex exec --help` of codex-cli 0.156.1; recheck on the installed version.

`launch.py` builds: `exec --json -o <run-dir>/last.txt -C <repo> -s <sandbox> -m <model> -c model_reasoning_effort="<level>" -` (prompt from stdin; `--skip-git-repo-check` outside Git). With `--json`, stdout is JSONL events: `thread.started` carries `thread_id`, `turn.completed` carries token usage, `agent_message` items carry the text. `-o` writes the final message to a file. `--output-schema <file>` can enforce the handoff fields.

| Role | Flags |
|---|---|
| Reviewer / researcher | `-s read-only` |
| Implementer in its scope | `-s workspace-write` (add `--add-dir` only for directories the packet owns) |
| Isolated writer | add `--worktree` |
| Outside a Git repository | add `--skip-git-repo-check` |
| Disposable run (no resume needed) | add `--ephemeral` |

- Never `--dangerously-bypass-approvals-and-sandbox` or `--dangerously-bypass-hook-trust`.
- Resume only by recorded ID: `codex exec resume <thread-id>`, never `--last`, never concurrently.
- Effort values depend on the model and account; read them from the inventory, not from this file.
- The `model` in `~/.codex/config.toml` (the desktop app's choice) may be refused by the CLI: on 2026-10-23 `gpt-6.1-sol` failed at once with "model is not supported when using Codex with a ChatGPT account". The models the account offers are the `slug`s in `~/.codex/models_cache.json` (visibility `list`); pass one with `--model` and record it in the inventory.
- `codex exec review` runs a non-interactive code review of the current repository: a cheap independent reviewer.

### Images through Codex (verified 2026-10-21)

A probe run (`codex exec ... -s workspace-write`, lightweight model) generated an image headless. The built-in tool saved it as `$CODEX_HOME/generated_images/<thread_id>/exec-*.png`. Without guidance the worker then copied the file by pasting base64 through about 30 shell commands, one of which failed on Windows command length: about 380k input tokens for one icon.

So the packet must say: **generate only; do not copy, encode or move the file; reply with the image path.** The coordinator then copies the newest file from `$CODEX_HOME/generated_images/<thread_id>/` (thread ID from the `thread.started` event) into the project and inspects it. Ask for transparency explicitly when needed and check the alpha channel afterwards.

Apps such as Canva or other connectors were not probed. Treat each as unknown until a small run succeeds; sign-in or consent prompts end the run as a blocker.

## Additional backends

Add only user-selected available connections or explicitly requested integrations. Inventory endpoint/provider, model/effort support, tools, data/billing boundary and actual-result metadata. Store no credentials.

Fallback stays inside the authorized pool. Network failure, quota exhaustion, unsupported model or approval rejection does not authorize another external service. Report missing access and continue independent permitted work.
