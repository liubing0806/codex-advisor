# Codex Advisor A/B benchmark

Run with an authenticated Codex CLI and the selected executor installed:

```bash
python3 benchmark/run.py --output /tmp/advisor-benchmark
```

Each task and arm launches a separate `codex exec` process in its own newly copied fixture workspace. There is no `resume` or shared conversation. The enabled prompt explicitly invokes `$codex-advisor` and supplies its local skill path; the disabled prompt forbids reading it. Both arms share task wording and initial project files. The runner preserves raw JSONL, stderr, final answer and independent test output, then writes `results.json`. Use the same model, authentication, executor availability and machine when comparing arms. Run from the repository checkout; no installation into the user skill directory is required. The CLI may need its normal authentication configuration. `--timeout` bounds each invocation in seconds.

The counter fixture has a failing negative-step test in the initial state; its prompt calls for an executor correction after a deliberately flawed first attempt, but a real executor is not guaranteed to make that error. Interpret the correction metric with the raw trace. The unavailable fixture tests fail-closed behavior; ensure Grok is unavailable for that run, or treat it as a different scenario. The runner never injects a fake executor into live trials. Keep runs whose preconditions differ separate in analysis.

Replay the deterministic *synthetic trace* used to exercise the scorer (these are **not** measured model outcomes):

```bash
python3 benchmark/run.py --replay benchmark/examples/synthetic.json --output /tmp/advisor-replay
python3 -m unittest discover -s benchmark -p 'test_*.py'
```

`results.schema.json` describes the machine output. Metrics are fractions/booleans; `null` means the event stream does not establish the fact. Overall score averages only observed metrics. `changed` comes from SHA-256 comparison of fixture files, including added/deleted files; `scope` checks exact paths. Direct edits, delegations and independent verification use observable tool-call events, not final prose. Tool calls hidden behind shell scripts or unsupported CLI event formats may yield false negatives; inspect preserved JSONL and diff before treating a score as conclusive. Contract completeness is assessed from the delegation payload's required fields, not semantic correctness. Requirement coverage is literal matching, so manual review remains necessary. Time uses wall clock; token usage is taken from CLI JSON when exposed, while `cost` stays `null` absent reliable billing data. Authentication failures, timeouts and missing executors remain in results rather than being silently discarded.
