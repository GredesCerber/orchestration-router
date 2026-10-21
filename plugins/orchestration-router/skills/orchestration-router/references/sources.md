# Documentation basis

Reviewed 2026-10-21. These explain mechanisms, not permanent model availability. Scheduling defaults and routing tiers are our operational design, not a benchmarked algorithm.

- [OpenAI: Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents): bounded assignments, separate context, model/effort choices, own token consumption and care with concurrent writes.
- [Anthropic: Building effective agents](https://www.anthropic.com/research/building-effective-agents): routing, orchestrator/workers and evaluator/optimizer are separate patterns. Conceptual older guidance; current client docs govern commands.
- [Claude Code: Subagents](https://code.claude.com/docs/en/sub-agents): model/effort inheritance and overrides, version-dependent behavior and nested contexts.
- [Claude Code: Model configuration](https://code.claude.com/docs/en/model-config): model-specific effort support/resolution; same effort names do not imply equal reasoning across models.
- [OpenRouter: Auto Router](https://openrouter.ai/docs/guides/routing/routers/auto-router): service-side task/model routing and actual-model metadata; market signals are not project quality evidence.
- [OpenRouter: Provider selection](https://openrouter.ai/docs/guides/routing/provider-selection): provider choice is separate from model choice.
- [OpenAI: Pricing and usage limits](https://learn.chatgpt.com/docs/pricing): current limits are available on the usage dashboard and via /status in an active CLI session.
- [Claude Code: Usage and costs](https://code.claude.com/docs/en/costs): /usage distinguishes plan bars from session cost estimates and can show last-known cached values after a quota-endpoint error.

- [Claude Code: Status line](https://code.claude.com/docs/en/statusline): `rate_limits.five_hour` / `seven_day` with `used_percentage` and `resets_at` in the statusline JSON (Pro/Max, after the first response).
- [chu459/claude-code-orchestrator-skill](https://github.com/chu459/claude-code-orchestrator-skill), seen via its Glama listing only: a Codex skill driving Claude Code with read-only default, per-run logs and post-run scope checks. Ideas borrowed; not installed or audited.

Local read-only creation check: Claude Code 2.1.296; help exposes model, effort, resume, agents, output-format and max-budget-usd. No model session or paid API was launched for this skill. Revision 2026-10-21 (Claude): launch recipe built from `--help` of 2.1.296; argument quoting checked on PowerShell 7.6 with a Python argv echo; the full `claude -p` launch was not run.
