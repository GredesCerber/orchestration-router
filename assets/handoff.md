# Handoff (worker return)

Ask workers to end with exactly this block. For Claude CLI, `--json-schema` can enforce the same fields as structured output.

```text
Task ID:
Status: done | partial | blocked | failed
Changed files (or commit):
Checks run, with result (command → pass/fail, screenshot path, etc.):
Not checked:
Unresolved issues / risks:
Scope deviations (files touched outside the packet, and why):
Processes left running (PID, port) or "none":
Session ID (if resumable):
Actual model / effort (only if reported by the runtime, else "unknown"):
Next step suggested:
```

The coordinator verifies this against the diff and logs before marking the task done. No secrets, no full trace dumps, no claims about checks that did not run.
