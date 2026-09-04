# Grok CLI adapter

Use this reference only when Grok is the selected executor.

## Invocation

Create the executor request with `mktemp`, then run:

```bash
scripts/run-grok.sh \
  --workspace "$(pwd)" \
  --spec "$SPEC_FILE" \
  --output "$REPORT_FILE" \
  --timeout 600
```

The adapter performs these checks before execution:

```bash
command -v grok
grok --version
grok models
```

It invokes Grok with:

```text
grok --prompt-file <spec> \
  --permission-mode acceptEdits \
  --allow Edit(<workspace>/**) \
  --allow Write(<workspace>/**) \
  --sandbox workspace \
  --output-format plain \
  --cwd <workspace>
```

It intentionally passes no `--model` or reasoning-effort option. Grok therefore uses the user's current CLI default.

The explicit `Edit` and `Write` rules are required for non-interactive file changes and are scoped to the selected workspace. The `workspace` sandbox adds operating-system filesystem restrictions to Grok and its child processes. `acceptEdits` remains enabled, and the adapter never uses blanket `--always-approve`. Grok may be unable to run some verification commands under this permission mode; the advisor must run the required verification independently.

## Exit status

- `0`: Grok exited successfully. This is not proof that the task is complete.
- `20`: the Grok executable is unavailable or its version check failed.
- `21`: `grok models` could not confirm an authenticated, usable session.
- `22`: Grok returned another execution failure.
- `124`: the configured timeout expired.

Read the output file for the exact Grok response or error. If the adapter returns a nonzero status, do not fall back to Codex and do not select another executor automatically.
