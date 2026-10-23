# Read-only quota checks

## When and how often

Check once at stage entry, before a substantial wave/provider switch, and after an actual quota error or user-reported reset. Reuse a recent snapshot during ordinary small tasks. A practical initial cache age is 15 minutes; shorten it for rapid consumption or a near-exhausted pool. This is our operational preference, not a provider guarantee. Refresh after heavy parallel work when the next routing decision depends on it.

Do not add a background monitor, recurring automation, paid diagnostic request, account integration or global setting just to make checking convenient. A failed usage endpoint is not necessarily exhausted work allowance.

## Codex / GPT subscription

Prefer the available native read-only usage tool, discovered by its description. In the Codex desktop environment this may be `mcp__codex_app__get_usage_limits` / `get_usage_limits`. Do not assume the same exact tool exists in another client.

For that tool's current contract:
- Prefer `rateLimitsByLimitId` when provided; legacy `rateLimits` may repeat the same pool and must not be added again.
- `usedPercent` is consumption: remaining = clamp(100 - usedPercent, 0, 100). Missing/null is unknown, not zero. Respect the actual tool contract if it changes.
- Each primary/secondary bucket has its own duration/reset; report both without summing percentages. Multiple model routes can share that same account pool.
- `credits` is separate from included plan allowance. Zero extra credits does not mean the included subscription quota is exhausted.
- Respect explicit blocking/spend-control signals even when a percentage seems positive; record the discrepancy and recheck once rather than trying to bypass it.

When the coordinator is not Codex (for example Claude Code driving Codex), run `python -B <skill-dir>/scripts/codex_usage.py`. It reads the last `rate_limits` (primary = 5-hour, secondary = weekly by `window_minutes`) from local Codex session logs. This is an observed local format, not a documented API; the values are last-known as of `checked_at`, and a failed parse means unknown.

If no native usage tool exists, use an existing accessible `/status` screen or the official usage dashboard within authorized access. Do not start a second CLI/session or a new authenticated service solely to inspect quota. Request the user's values if the decision genuinely needs them.

## Claude Code

Prefer an already exposed authorized read-only quota capability.

**Statusline snapshot (documented, preferred when set up).** Claude Code passes the statusline script JSON that, for Pro/Max subscribers after the first response in a session, includes `rate_limits.five_hour` and `rate_limits.seven_day` with `used_percentage` (0–100) and `resets_at` (Unix seconds); each window may be absent ([docs](https://code.claude.com/docs/en/statusline)). [`scripts/claude_usage_statusline.py`](../scripts/claude_usage_statusline.py) prints a short status line and writes just those fields plus a timestamp to `~/.claude/usage-snapshot.json` (or `$CLAUDE_USAGE_SNAPSHOT`), in the snapshot shape below; the coordinator reads that file. Installing it changes the user's global Claude Code settings, so do it only with the user's explicit permission. The file reflects the last interactive session that rendered a statusline: label it with its `checked_at` and treat it as stale when old. Print-mode runs do not render a statusline.

Otherwise the built-in interactive `/usage` screen provides plan usage information where supported by that installed version/account. Inspect the existing idle session only through available permitted tools; do not interrupt its worker or resume it concurrently for this purpose.

`/usage` is an interactive client command, not proof that `claude -p '/usage'`, a shell `claude usage` subcommand, or a model answering about its limits is a supported quota API. Do not invent such commands. If no safe access exists, ask the user for the usage bars/reset times or a screenshot; mark the result user-reported.

Distinguish plan usage bars from session token/cost estimates. `/cost`/session totals do not by themselves reveal remaining subscription allowance. Cached usage can be displayed after an endpoint error: preserve its last-known timestamp and label it stale. A usage endpoint's own cooldown is not the plan's work-quota reset.

Do not read credential stores, dump environment variables, extract OAuth tokens or call undocumented private quota endpoints. Do not use `/insights` as a cheap quota check: it is analysis work, not an allowance read.

### No quota access (cloud or remote host)

A cloud session usually has no statusline snapshot and no `/usage` screen. Record the pool as `freshness: "unknown"` with empty windows and proceed at the project's worker cap; do not ask the user for numbers unless a routing decision depends on them. A usage-limit error from a child is the signal to stop spawning on that pool.

## Other selected providers

Use their documented read-only quota/balance tools only when available and authorized. Account balance, requests/tokens per minute, monthly spend cap and subscription percentage are not interchangeable. Do not infer a number of future tasks from a remaining percentage or price estimate.

## Snapshot and routing policy

Keep a sanitized record alongside the existing project inventory, never in a public repository:

```json
{
  "pool": "codex-default",
  "source": "native read-only usage tool",
  "checked_at": "ISO-8601 timestamp from this check",
  "freshness": "current",
  "windows": [
    {"label": "5h", "used_percent": null, "remaining_percent": null, "resets_at": null},
    {"label": "weekly", "used_percent": null, "remaining_percent": null, "resets_at": null}
  ],
  "blocked": null
}
```

The example is a schema illustration, not measured usage. Preserve known zeros; leave unavailable values null. Store no account IDs, credential strings, payment details or raw account response. Bind all candidates that share a pool to this one snapshot rather than multiplying allowance by worker count.

If service thresholds are not given, use simple operator bands only as routing advice: at or below 20% remaining in any applicable window, avoid broad fan-out; at or below 5%, preserve capacity for completion/checkpoint and essential verification. The user may choose other bands. These bands are not provider rules, predicted costs or permission to downgrade a required model/effort. Inexpensive adequate routes can continue; confirmed exhausted routes wait.

After an indicated reset time passes, obtain fresh evidence before calling an exhausted route available. User-supplied or cached values stay labeled with their source/time. Show times in the user's timezone, preserving UTC/offset in stored timestamps. Do not guess a reset from the machine clock or a historical schedule.

The offline planner does not fetch/normalize live usage or enforce shared quota. The coordinator must apply the snapshot before planning: set candidate `status` to `quota_exhausted` for confirmed unavailable routes and reduce max_workers when appropriate. Unknown quota is not a failed login or a ready unlimited pool.
