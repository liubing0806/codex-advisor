#!/usr/bin/env bash

set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
adapter="$repo_root/plugins/codex-advisor/skills/codex-advisor/scripts/run-grok.sh"
test_root=$(mktemp -d -t codex-advisor-test.XXXXXX)
trap 'rm -rf "$test_root"' EXIT

fake_bin="$test_root/fake bin"
workspace="$test_root/work tree"
spec_file="$test_root/task spec.txt"
output_file="$test_root/agent output.txt"
args_file="$test_root/grok args.txt"

mkdir -p "$fake_bin" "$workspace"
printf '%s\n' 'EXECUTOR REQUEST' > "$spec_file"

cat > "$fake_bin/grok" <<'FAKE_GROK'
#!/usr/bin/env bash
set -u

case "${1:-}" in
  --version)
    printf '%s\n' 'grok test-version'
    exit 0
    ;;
  models)
    if [[ "${FAKE_GROK_AUTH_FAIL:-0}" == 1 ]]; then
      printf '%s\n' 'test authentication failure' >&2
      exit 7
    fi
    printf '%s\n' 'Default model: test-default'
    exit 0
    ;;
esac

printf '%s\n' "$@" > "$FAKE_GROK_ARGS"
if [[ "${FAKE_GROK_SLEEP:-0}" != 0 ]]; then
  sleep "$FAKE_GROK_SLEEP"
fi
printf '%s\n' "${FAKE_GROK_OUTPUT:-EXECUTOR REPORT}"
exit "${FAKE_GROK_EXIT:-0}"
FAKE_GROK
chmod +x "$fake_bin/grok"

PATH="$fake_bin:/usr/bin:/bin" FAKE_GROK_ARGS="$args_file" \
  "$adapter" --workspace "$workspace" --spec "$spec_file" --output "$output_file" --timeout 5

rg -Fx -- '--permission-mode' "$args_file" >/dev/null
rg -Fx -- 'acceptEdits' "$args_file" >/dev/null
rg -Fx -- '--allow' "$args_file" >/dev/null
rg -Fx -- "Edit($workspace/**)" "$args_file" >/dev/null
rg -Fx -- "Write($workspace/**)" "$args_file" >/dev/null
rg -Fx -- '--sandbox' "$args_file" >/dev/null
rg -Fx -- 'workspace' "$args_file" >/dev/null
rg -Fx -- '--output-format' "$args_file" >/dev/null
rg -Fx -- 'plain' "$args_file" >/dev/null
rg -Fx -- '--cwd' "$args_file" >/dev/null
rg -Fx -- "$workspace" "$args_file" >/dev/null
if rg -x -- '--model|-m' "$args_file" >/dev/null; then
  printf '%s\n' 'adapter unexpectedly pinned a model' >&2
  exit 1
fi
if rg -Fx -- '--always-approve' "$args_file" >/dev/null; then
  printf '%s\n' 'adapter unexpectedly enabled blanket approval' >&2
  exit 1
fi
rg -F -- 'EXECUTOR REPORT' "$output_file" >/dev/null

set +e
PATH='/usr/bin:/bin' "$adapter" \
  --workspace "$workspace" --spec "$spec_file" --output "$output_file" --timeout 5
test_rc=$?
set -e
[[ $test_rc -eq 20 ]]
rg -F -- 'grok not found on PATH' "$output_file" >/dev/null

set +e
PATH="$fake_bin:/usr/bin:/bin" FAKE_GROK_ARGS="$args_file" FAKE_GROK_AUTH_FAIL=1 \
  "$adapter" --workspace "$workspace" --spec "$spec_file" --output "$output_file" --timeout 5
test_rc=$?
set -e
[[ $test_rc -eq 21 ]]
rg -F -- 'test authentication failure' "$output_file" >/dev/null

set +e
PATH="$fake_bin:/usr/bin:/bin" FAKE_GROK_ARGS="$args_file" FAKE_GROK_EXIT=9 \
  "$adapter" --workspace "$workspace" --spec "$spec_file" --output "$output_file" --timeout 5
test_rc=$?
set -e
[[ $test_rc -eq 22 ]]
rg -F -- 'GROK_EXIT_CODE: 9' "$output_file" >/dev/null

set +e
PATH="$fake_bin:/usr/bin:/bin" FAKE_GROK_ARGS="$args_file" FAKE_GROK_SLEEP=2 \
  "$adapter" --workspace "$workspace" --spec "$spec_file" --output "$output_file" --timeout 1
test_rc=$?
set -e
[[ $test_rc -eq 124 ]]
rg -F -- 'STATUS: timeout after 1 seconds' "$output_file" >/dev/null

printf '%s\n' 'run-grok adapter tests passed'
