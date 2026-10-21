# Task packet

Copy, fill every line, send as the worker's prompt (UTF-8 file or stdin). Write "none" rather than deleting a line. If the project has its own task template, use that one instead.

```text
Task ID:
Goal (one sentence, observable result):
Executor / model / effort, and why:
Base revision (commit) and workspace (absolute path, worktree or branch):
Owned paths (may write):
Read-only paths:
Do not touch:
Shared resources reserved (port, DB copy, build dir, browser), and who owns the rest:
Dependencies already accepted:
Context (only needed links/files; no chat history):
Acceptance criteria (concrete commands, screens, data):
Tools allowed (and permission mode for Claude CLI):
Data boundary (what must not leave the machine / be printed):
Delegation allowance (default: none):
Stop and return if: two attempts fail without a new cause, scope must grow, or access is missing
Output location (result files):
Return format: assets/handoff.md
```

Keep the packet short. A reviewer's packet states what to check, not the expected verdict.
