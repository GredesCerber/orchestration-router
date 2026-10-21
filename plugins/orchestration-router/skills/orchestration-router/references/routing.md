# Routing policy

## Separate layers

| Layer | Decision | Evidence |
|---|---|---|
| Orchestrator | tasks, dependencies, owners, integration | ledger and accepted artifacts |
| Model router | eligible model for a packet | requested model and reason |
| Effort selector | supported reasoning setting | requested vs reported actual effort |
| Provider router | service serving an API model | reported provider, when exposed |
| Scheduler | ready packets that can run now | bounded wave with exclusive resources |

A skill supplies rules; it does not turn subscriptions into API credits, expose hidden account models or create a gateway.

## Current catalog

Use native tool metadata, client help, account model picker/status and observed run metadata. Record sources/timestamps, not credentials. A failed route does not prove its whole model family unavailable. Do not probe many paid models for discovery.

Map locally chosen roles, not universal benchmarks:

| Packet | Initial preference if available | Effort starting point |
|---|---|---|
| Bounded extraction/search/classification, source discovery, repository/license metadata | available lightweight GPT or Claude Haiku | low or supported default; medium for multi-source factual checks |
| Defined-contract implementation | ordinary coding GPT or Claude Sonnet | medium |
| Ambiguous cross-module bug, architecture, hard refactor | strong reasoning GPT or Claude Opus | high; increase for a demonstrated need |
| Independent review | separate capable worker; cross-model if useful | medium/high by consequences |
| Visual/media/document operations | executor with the actual authoring/rendering tool | effort cannot replace missing tools |

Refresh IDs from availability; concrete model names belong in the project inventory or project rules, not here. These are initial heuristics, not claims one family always wins. Explicit user selections and project tables take precedence.

Split research discovery from decisions that need deeper judgment. Finding official URLs, checking a LICENSE file and collecting maintenance dates belongs to the lightweight packet even inside a complex project. Escalate an uncertain reuse condition or integration tradeoff with the collected evidence, rather than assigning all preliminary searching to the strongest model.

## Effort is independent

Choose a supported value near the required depth. A model without exposed effort can remain eligible: report default/null, not fabricated high.

- Supported sets differ by model/backend. Same labels are not calibrated equally across models.
- Managed settings or the harness may override/clamp requests; actual remains unknown unless exposed.
- Missing context/tools, network failures and conflicting requirements are not reasoning deficiencies.
- Maximum effort is a justified choice for one hard packet, not the backlog default.

## Profiles and escalation

`economy`: lowest observed cost preference among adequate candidates; do not put every task on the smallest model.
`balanced`: adequate depth and observed fit, then cost/latency.
`quality`: favor strong reasoning for complex tasks and independent review, without automatic duplication or unlimited effort.

An explicit allocation preference (SKILL.md, step 3) overrides the default economic preference; it does not raise the tier of routine work. Paid API fallback still needs its own authorization.

Use real recent acceptance, substantive failure, latency and consumption when available. Ordinal `cost_rank` is only a local preference, never dollar pricing or measured savings. Do not classify solely by prompt length.

Promote with the failing case and acceptance criteria; demote clear follow-up work after hard decisions are resolved. Do not silently replace a user-mandated model.

## Optional OpenRouter

Default execution needs no API account. Before implementing API calls, read current official docs and obtain the necessary authorized connection/billing scope.

For selected OpenRouter use, constrain models, cost policy, tools/modalities and data/provider policies. `openrouter/auto` is service-side model selection, not a scheduler or file-lock manager. Log the response's actual model, which may change between turns. Market usage/spend is not proof of project correctness.

Do not reuse subscription access as API credentials, enable paid fallback, or transmit private data just because an adapter is listed. Clarify an unknown spending ceiling before paid requests.
