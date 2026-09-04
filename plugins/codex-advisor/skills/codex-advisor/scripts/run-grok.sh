#!/usr/bin/env bash

set -uo pipefail

readonly EXIT_UNAVAILABLE=20
readonly EXIT_AUTH=21
readonly EXIT_EXECUTION=22
readonly EXIT_TIMEOUT=124

usage() {
  printf '%s\n' 'Usage: run-grok.sh --workspace <dir> --spec <file> --output <file> [--timeout <seconds>]' >&2
}

workspace=''
spec_file=''
output_file=''
timeout_seconds=600

while (($# > 0)); do
  case "$1" in
    --workspace)
      [[ $# -ge 2 ]] || { usage; exit 2; }
      workspace=$2
      shift 2
      ;;
    --spec)
      [[ $# -ge 2 ]] || { usage; exit 2; }
      spec_file=$2
      shift 2
      ;;
    --output)
      [[ $# -ge 2 ]] || { usage; exit 2; }
      output_file=$2
      shift 2
      ;;
    --timeout)
      [[ $# -ge 2 ]] || { usage; exit 2; }
      timeout_seconds=$2
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$workspace" || -z "$spec_file" || -z "$output_file" ]]; then
  usage
  exit 2
fi

if [[ ! "$timeout_seconds" =~ ^[1-9][0-9]*$ ]]; then
  printf 'Timeout must be a positive integer: %s\n' "$timeout_seconds" >&2
  exit 2
fi

if [[ ! -d "$workspace" ]]; then
  printf 'Workspace does not exist: %s\n' "$workspace" >&2
  exit 2
fi

if [[ ! -f "$spec_file" ]]; then
  printf 'Spec file does not exist: %s\n' "$spec_file" >&2
  exit 2
fi

output_parent=$(dirname -- "$output_file")
if [[ ! -d "$output_parent" ]]; then
  printf 'Output directory does not exist: %s\n' "$output_parent" >&2
  exit 2
fi

workspace=$(cd "$workspace" && pwd -P) || exit 2
spec_parent=$(cd "$(dirname -- "$spec_file")" && pwd -P) || exit 2
spec_file="$spec_parent/$(basename -- "$spec_file")"
output_parent=$(cd "$output_parent" && pwd -P) || exit 2
output_file="$output_parent/$(basename -- "$output_file")"

: > "$output_file" || exit 2

if ! grok_bin=$(command -v grok); then
  printf '%s\n' 'STATUS: unavailable' 'REASON: grok not found on PATH' > "$output_file"
  exit "$EXIT_UNAVAILABLE"
fi

if ! version_output=$("$grok_bin" --version 2>&1); then
  printf '%s\n' 'STATUS: unavailable' 'REASON: grok version check failed' "$version_output" > "$output_file"
  exit "$EXIT_UNAVAILABLE"
fi

if ! models_output=$("$grok_bin" models 2>&1); then
  printf '%s\n' 'STATUS: unavailable' 'REASON: grok authentication or model discovery failed' "$models_output" > "$output_file"
  exit "$EXIT_AUTH"
fi

grok_command=(
  "$grok_bin"
  --prompt-file "$spec_file"
  --permission-mode acceptEdits
  --allow "Edit($workspace/**)"
  --allow "Write($workspace/**)"
  --disallowed-tools run_terminal_cmd
  --sandbox workspace
  --output-format plain
  --cwd "$workspace"
)

timeout_bin=$(command -v gtimeout || command -v timeout || true)
if [[ -z "$timeout_bin" ]]; then
  printf '%s\n' 'WARN: timeout/gtimeout not found; Grok invocation is uncapped' >> "$output_file"
  "${grok_command[@]}" >> "$output_file" 2>&1
  run_status=$?
else
  "$timeout_bin" "$timeout_seconds" "${grok_command[@]}" >> "$output_file" 2>&1
  run_status=$?
fi

case "$run_status" in
  0)
    exit 0
    ;;
  124)
    printf '\nSTATUS: timeout after %s seconds\n' "$timeout_seconds" >> "$output_file"
    exit "$EXIT_TIMEOUT"
    ;;
  *)
    printf '\nSTATUS: execution failure\nGROK_EXIT_CODE: %s\n' "$run_status" >> "$output_file"
    exit "$EXIT_EXECUTION"
    ;;
esac
