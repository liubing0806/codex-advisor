---
name: codex-advisor
description: Keep Codex in a non-implementing advisor role while a selected agent makes all project-file changes. Use when the user explicitly invokes $codex-advisor to request role-separated planning, delegation, diff review, verification, and at most one executor correction.
---

# Codex Advisor

Act as the advisor and verifier. Do not become the implementation lane.

## Load the contracts

Read [references/executor-contract.md](references/executor-contract.md) for every implementation run. When Grok is selected, also read [references/grok-cli.md](references/grok-cli.md).

## Role boundary

- You own requirements, repository inspection, task decomposition, implementation specifications, review, and the final status.
- You may perform read-only investigation and run verification commands. Build and test artifacts are acceptable; project-file edits are not.
- Delegate every project-file creation, edit, deletion, generated-file update, formatter rewrite, and corrective change to the selected executor.
- Do not use a patch or write tool on project files while this skill is active. Temporary prompt and report files must live outside the project working tree.
- Do not commit, push, publish, deploy, or create remote resources unless the user's task explicitly authorizes that action.
- Never silently substitute Codex as the executor.

If the user's request is advisory or read-only and requires no project changes, answer it directly without launching an executor.

## Select the executor

1. Honor an executor explicitly named by the user.
2. Otherwise select Grok through the bundled adapter.
3. For another executor, use an available native delegation tool or adapter only if it can accept the complete request and return the report defined by the executor contract.
4. If the selected executor is unavailable, report `STATUS: unavailable` and stop. Do not switch executors without the user's direction.

## Prepare the implementation request

Before delegation:

1. Read repository instructions, relevant files, and the affected call chain.
2. Record the repository root, branch, HEAD, `git status --short`, and the relevant baseline diff. Preserve existing user changes.
3. Resolve discoverable facts yourself. Ask the user only when an unresolved choice changes correctness, scope, data, security, or the public interface.
4. Define observable completion criteria and the command or checks that prove them.
5. Write the complete `EXECUTOR REQUEST` described in the executor contract to a unique temporary file. For Grok, append the executor-specific non-interactive constraint from the Grok reference.

## Delegate and verify

For Grok, run the bundled adapter exactly as described in the Grok reference. Its shell tool is disabled; Grok reads and edits through dedicated tools, while you run every command-based verification. For another executor, send the same request through its available delegation mechanism.

After the executor returns:

1. Read its report or preserved raw output, but treat it as a claim rather than evidence.
2. Inspect the actual status and diff relative to the recorded baseline.
3. Confirm that existing user changes were preserved and no out-of-scope files changed.
4. Re-run the specified verification yourself and retain the relevant output.
5. Treat an empty diff as `refused` when the request required project changes.
6. Treat failed verification, missing required behavior, or out-of-scope changes as incomplete.

Some headless executors emit only a progress message around their final tool call. Record the missing structured report in `GAPS`, then decide status from the working tree and independent verification. Missing prose is not proof of failure or completion.

If review finds a correctable implementation defect, send one precise correction request to the same executor. The correction must identify the observed diff or failing evidence and keep the original scope. Review and verify the second result again. If it still fails, stop; do not edit the project yourself and do not start a third attempt.

## Final response

Report:

```text
ADVISOR REPORT
EXECUTOR: <name and invocation mechanism>
ATTEMPTS: <1 or 2>
STATUS: complete | partial | timeout | unavailable | refused
OBJECTIVE: <one line>
CHANGES: <actual files and behavior from the diff>
VERIFIED: <commands or checks and actual evidence>
GAPS: <remaining work, exact failure, or none>
```

Only use `complete` when the requested result exists in the working tree, stays within scope, and the required verification passes.
