# Executor contract

Use this contract for every executor, whether it is reached through a native delegation tool or an external CLI adapter.

## Request

Send one self-contained request with this shape:

```text
EXECUTOR REQUEST
ATTEMPT: 1 | 2
OBJECTIVE: <the observable result>
WORKSPACE: <absolute working directory>
ALLOWED CHANGES: <exact files or bounded subsystem>
INTERFACES: <signatures, schemas, commands, or none>
CONSTRAINTS: <repository rules, preserved behavior, forbidden actions>
VERIFICATION: <commands or observable checks>
BASELINE: <branch, HEAD, dirty paths, and user changes that must be preserved>

Implement the request in the stated workspace. Inspect the relevant code before editing.
Run verification when your permissions allow it. Do not commit, push, deploy, publish,
or modify anything outside ALLOWED CHANGES unless the request explicitly authorizes it.
Return the EXECUTOR REPORT below.
```

The request must contain all decisions the advisor has already made. Do not delegate unresolved product, data, security, or public-interface decisions.

## Report

Require this response:

```text
EXECUTOR REPORT
EXECUTOR: <agent and mechanism>
STATUS: complete | partial | timeout | unavailable | refused
OBJECTIVE: <one line>
CHANGES: <file and behavior, based on the actual working tree>
VERIFIED: <command and actual result, or not run with reason>
GAPS: <missing information or unfinished work, or none>
ERROR: <exact error when status is not complete, or none>
```

An executor process exiting successfully does not prove `complete`. The advisor makes the final status decision after inspecting the working tree and rerunning verification.

If an executor integration ends after its final tool call and provides only raw progress output, preserve that output unchanged. The advisor records the missing structured report in `GAPS` and derives the final status from the actual diff and independent verification.

## Adapter requirements

An executor adapter must:

- accept an absolute workspace path, a request file, an output file, and a bounded timeout;
- preserve spaces and special characters in paths without evaluating them as shell text;
- use the named executor without silently substituting another agent;
- constrain writes to the requested workspace and avoid blanket approval modes when a narrower edit mode exists;
- retain the executor's final output and return a distinct status for unavailable, authentication failure, timeout, and execution failure;
- avoid committing, pushing, publishing, deploying, or changing user-level configuration.

To add another external CLI, add `scripts/run-<executor>.sh` with the same arguments and exit codes as `run-grok.sh`, document only its executor-specific behavior, and leave the advisor workflow unchanged.
