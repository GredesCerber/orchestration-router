# Executor adapters

Start with `python -B <skill-dir>/scripts/discover.py`: it lists agent CLIs on PATH, versions and visible capability flags without starting a model or reading credentials. Everything it returns is unconfirmed until the user's choices and a first run say otherwise.

The same adapters work from any host. Codex can drive Claude Code; Claude Code can drive Codex; another harness can drive both. The coordinator is whoever loaded this skill.

## Native subagents (current host)

Use the host's actual spawn tool, model/effort options and concurrency limits. Omitted settings can inherit the parent. Some hosts restrict overrides on full-history forks; prefer a compact packet when choosing the worker model. Do not change global config to work around missing per-worker control.

Read-only is a tool boundary, not a worker name. Children may not share the parent's tools, sign-ins or skills: pass exact paths, instructions and context.

## Route by capability first

Some tools exist in only one executor. Send the packet where the tool is, then pick the model inside that executor:

| Need | Typical owner |
|---|---|
| Raster image generation/editing | Codex (`image_gen` built-in, `imagegen` system skill) |
| Codex apps/plugins and their skills (documents, slides, connectors the user enabled in Codex) | Codex |
| Claude Code skills, subagents, hooks, MCP servers configured for Claude | Claude Code |
| Browser or desktop control | whichever host has it connected; headless CLI runs usually do not |

A feature flag or an installed plugin proves the tool exists, not that it works headless or that its account is connected. The first use of a capability through a CLI is a small probe; record the result in the inventory. An app that needs sign-in or consent cannot get it in a background run: return a blocker instead.

## Launching a CLI worker (any CLI, Windows PowerShell)

Run each worker in the background with its own folder, the prompt in a UTF-8 file, and logs on disk:

```powershell
$run = "<project>\work\orchestration\<task-id>"   # absolute path from the packet
New-Item -ItemType Directory -Force $run | Out-Null
# packet.txt: assets/packet.md filled in, saved as UTF-8
$cliArgs = @(<flags from the adapter below>)
# Start-Process splits array elements on spaces (checked on PowerShell 7.6), so quote each one.
# Valid only while no element contains a double quote.
$argLine = ($cliArgs | ForEach-Object { '"' + $_ + '"' }) -join ' '
$p = Start-Process <claude|codex> -ArgumentList $argLine -WorkingDirectory '<repo>' -NoNewWindow -PassThru `
     -RedirectStandardInput "$run\packet.txt" -RedirectStandardOutput "$run\events.jsonl" `
     -RedirectStandardError "$run\stderr.txt"
$p.Id   # record in the ledger before doing anything else
```

- Poll with bounded waits: `Get-Process -Id <pid>`, the tail of `events.jsonl`, `git diff --name-only` in the worker's workspace.
- Never interpolate untrusted text into the argument list; it goes in `packet.txt`. Do not name the array `$args` (PowerShell automatic variable).
- Garbled Cyrillic is console encoding: keep prompts in UTF-8 files and set `[Console]::OutputEncoding = [Text.UTF8Encoding]::new()` in the launching shell.
- On macOS/Linux the same flags apply; use `nohup <cli> ... < packet.txt > events.jsonl 2> stderr.txt &` and record `$!`.
- A child inherits the parent's environment. Do not put secrets in the packet; prefer a minimal environment when the CLI supports it.
- A timeout does not prove the child exited. Reconcile process tree and diff before retry or replacement. Never kill unrelated or user processes.

## Claude Code

Flags from `claude --help` of 2.1.296; recheck on the installed version.

Installation is not authentication or quota. Claude Code in print mode (`-p`) is a full agent: give an implementation lead the tools its stage needs, keep reviewers read-only.

**Permissions decide whether a print-mode lead can work at all.** Nobody answers prompts in `-p`, so anything that would prompt is denied. Set the mode explicitly:

| Role | Flags |
|---|---|
| Reviewer / researcher | `--permission-mode plan` |
| Implementer in its scope | `--permission-mode acceptEdits --allowedTools "Bash(npm test:*) Bash(git diff:*) Bash(git status:*)"` (the project's real build/test commands) |
| Isolated writer | add `--worktree <task-id>` when worktrees are allowed and no shared runtime folder is involved |

Base flags: `-p --model <alias> --effort <level> --output-format stream-json --verbose --name <task-id>`. For a short single-shot task use `--output-format json`. `--json-schema '<schema>'` can enforce the handoff fields. The final `result` event holds `session_id`, usage and the final text.

- Never `--dangerously-skip-permissions` / `bypassPermissions`. `--add-dir` only for directories the packet owns.
- Resume only by recorded ID (`--resume <session-id>`), never concurrently, never "latest".
- Print mode loads project configuration (CLAUDE.md, settings, hooks): use a trusted cwd.
- Model resolution: aliases are not exact versions; `CLAUDE_CODE_SUBAGENT_MODEL`, `CLAUDE_CODE_EFFORT_LEVEL` and managed settings can override requests. Do not change them globally. Supported effort is model-specific.
- Nested workers: give an explicit allowance and count them in the project cap; a prompt cap is advisory. `--max-budget-usd` bounds API spend only, not subscription quota.

The full `claude -p` launch was not run while writing this recipe (paid run); do one short trivial packet first.

## Codex CLI

Flags from `codex exec --help` of codex-cli 0.156.1; recheck on the installed version.

Base flags: `exec --json -o <run>\last.txt -C <repo> -m <model> -c model_reasoning_effort="<level>"`. With `--json`, stdout is JSONL events: `thread.started` carries `thread_id`, `turn.completed` carries token usage, `agent_message` items carry the text. `-o` writes the final message to a file. `--output-schema <file>` can enforce the handoff fields.

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
- `codex exec review` runs a non-interactive code review of the current repository: a cheap independent reviewer.

### Images through Codex (verified 2026-10-21)

A probe run (`codex exec ... -s workspace-write`, lightweight model) generated an image headless. The built-in tool saved it as `$CODEX_HOME/generated_images/<thread_id>/exec-*.png`. Without guidance the worker then copied the file by pasting base64 through about 30 shell commands, one of which failed on Windows command length: about 380k input tokens for one icon.

So the packet must say: **generate only; do not copy, encode or move the file; reply with the image path.** The coordinator then copies the newest file from `$CODEX_HOME/generated_images/<thread_id>/` (thread ID from the `thread.started` event) into the project and inspects it. Ask for transparency explicitly when needed and check the alpha channel afterwards.

Apps such as Canva or other connectors were not probed. Treat each as unknown until a small run succeeds; sign-in or consent prompts end the run as a blocker.

## Additional backends

Add only user-selected available connections or explicitly requested integrations. Inventory endpoint/provider, model/effort support, tools, data/billing boundary and actual-result metadata. Store no credentials.

Fallback stays inside the authorized pool. Network failure, quota exhaustion, unsupported model or approval rejection does not authorize another external service. Report missing access and continue independent permitted work.
