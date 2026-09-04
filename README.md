# Codex Advisor

Codex Advisor keeps Codex in the advisor role while another agent performs implementation work. Codex inspects the repository, resolves requirements, writes a self-contained implementation request, reviews the actual diff, reruns verification, and may ask the same executor for one correction.

The skill is explicit-only. It does not change ordinary Codex behavior unless you invoke `$codex-advisor`.

## Roles

- **Advisor:** Codex owns requirements, architecture, scope, verification, and the final status. It does not edit project files while the skill is active.
- **Executor:** The selected agent owns every project-file change. Grok is the default executor; another agent can be named when a compatible native delegation tool or adapter is available.
- **Failure policy:** An unavailable or failed executor is reported directly. Codex does not take over implementation or silently select another agent.

## Install

Add this repository as a Codex plugin marketplace, then install the plugin:

```bash
codex plugin marketplace add liubing0806/codex-advisor
codex plugin add codex-advisor@codex-advisor
```

Start a new Codex thread after installation so the skill is discovered.

The default executor requires the [Grok CLI](https://grok.com/) to be installed and authenticated:

```bash
grok login
grok models
```

Codex Advisor intentionally does not pin a Grok model. The adapter uses the default selected by the user's Grok CLI configuration.

## Use

Use the default Grok executor:

```text
$codex-advisor Add request rate limiting to this service. Preserve the public API and run the existing integration tests.
```

Name another executor and its available mechanism:

```text
$codex-advisor Use the available Claude executor for this task: migrate the parser without changing its public types.
```

For implementation tasks, the workflow is:

1. Codex reads repository instructions and the affected call chain.
2. Codex records the Git baseline and writes the executor contract.
3. The selected executor edits the project.
4. Codex reads the actual diff and reruns verification.
5. Codex may send one correction to the same executor, then reports the result.

The workflow does not authorize commits, pushes, deployments, publishing, or changes outside the requested workspace.

## Add an executor

All executors use the contract in `references/executor-contract.md`. A native delegation tool may carry that contract directly. An external CLI adapter should implement the same arguments and exit statuses as `run-grok.sh`:

```text
run-<executor>.sh --workspace <dir> --spec <file> --output <file> [--timeout <seconds>]
```

An adapter must use the named agent, preserve exact output, constrain writes to the workspace, and fail loudly when unavailable. It must not fall back to Codex.

## Develop and verify

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" \
  plugins/codex-advisor/skills/codex-advisor

python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator/scripts/validate_plugin.py" \
  plugins/codex-advisor

tests/run-grok-adapter-test.sh
```

## Acknowledgements

The role-separated architect and implementer pattern was inspired by [fable-advisor](https://github.com/DannyMac180/fable-advisor). Codex Advisor is a new Codex-native implementation with a generic executor contract.

## License

MIT
