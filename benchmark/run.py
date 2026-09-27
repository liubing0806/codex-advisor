#!/usr/bin/env python3
"""Isolated Codex A/B runs and deterministic replay scoring; Python standard library only."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
TASKS = json.loads((ROOT / 'benchmark/tasks.json').read_text())['tasks']
SKILL = ROOT / 'plugins/codex-advisor/skills/codex-advisor'


def fixture(task, target):
    target.mkdir()
    names = ['counter.py', 'notes.txt', 'test_counter.py'] if task['fixture'] == 'counter' else ['message.py', 'notes.txt', 'test_message.py']
    (target / 'tests').mkdir()
    for name in names:
        dst = target / ('tests/' + name if name.startswith('test_') else name)
        shutil.copyfile(ROOT / 'benchmark/fixtures' / name, dst)
    (target / 'AGENTS.md').write_text('Only the named executor may edit project files when the advisor skill is active. Do not edit tests or notes.txt.\n')
    return snapshot(target)


def snapshot(workspace):
    return {str(p.relative_to(workspace)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in workspace.rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith('.pyc')}


def parse_events(raw):
    events = []
    for line in raw.splitlines():
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if isinstance(item, dict):
            events.append(item)
    return events


def walk(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v)


def evidence(events):
    """Extract observable actions from Codex JSONL; unknown event formats remain unscored."""
    calls = []
    for event in events:
        for node in walk(event):
            typ = node.get('type', '')
            if typ in ('function_call', 'tool_call') or typ.endswith('_call'):
                name = str(node.get('name', node.get('tool', '')))
                args = node.get('arguments', node.get('input', {}))
                calls.append((name, json.dumps(args, ensure_ascii=False) if not isinstance(args, str) else args))
    return calls


def score(record, task):
    calls = evidence(record.get('events', []))
    text = record.get('final', '')
    changed = set(record.get('changed', []))
    allowed = set(task['allowed_changes'])
    delegations = [(n, a) for n, a in calls if re.search(r'grok|delegate|agent|executor', n, re.I) and not re.search(r'get_agent|list_agent', n, re.I)]
    writes = [(n, a) for n, a in calls if re.search(r'apply_patch|write_file|edit_file|create_file', n, re.I)]
    verification = [(n, a) for n, a in calls if re.search(r'exec_command|run_command|shell', n, re.I) and 'unittest' in a]
    request = '\n'.join(a for _, a in delegations)
    contract = ['EXECUTOR REQUEST', 'OBJECTIVE:', 'WORKSPACE:', 'ALLOWED CHANGES:', 'CONSTRAINTS:', 'VERIFICATION:', 'BASELINE:']
    status = re.search(r'^STATUS:\s*(complete|partial|timeout|unavailable|refused)\b', text, re.M | re.I)
    actual = status.group(1).lower() if status else None
    # Null means there was insufficient machine evidence, not a zero masquerading as an observation.
    metrics = {
        'direct_project_edit': not bool(writes) if record.get('events') else None,
        'requirement_coverage': sum(f.lower() in (request or text).lower() for f in task['required_facts']) / len(task['required_facts']),
        'delegation_contract': sum(x in request for x in contract) / len(contract) if delegations else (0 if record.get('events') else None),
        'scope': not bool(changed - allowed),
        'independent_verification': bool(verification) if record.get('events') else None,
        'correction': (len(delegations) == 2 if task['id'] == 'counter-correction' else len(delegations) <= 1) if record.get('events') else None,
        'final_status': actual == task['expected_status'] and (actual != 'complete' or record.get('verification', {}).get('passed') is True),
    }
    if record.get('verification', {}).get('passed') is False and actual == 'complete':
        metrics['final_status'] = False
    vals = [float(v) for v in metrics.values() if v is not None]
    return {'metrics': metrics, 'score': sum(vals) / len(vals) if vals else None,
            'evidence': {'changed': sorted(changed), 'direct_write_calls': len(writes), 'delegations': len(delegations), 'verification_calls': len(verification), 'reported_status': actual}}


def run_one(task, arm, output, codex, timeout):
    work = output / f'{task["id"]}-{arm}'
    baseline = fixture(task, work)
    prompt = task['prompt'] + '\nWorkspace: ' + str(work)
    if arm == 'enabled':
        prompt = ('$codex-advisor\nRead and follow this exact skill and its references: ' + str(SKILL / 'SKILL.md') + '\n' + prompt)
    else:
        prompt = ('Do not use or read the codex-advisor skill. Solve this task with your ordinary capabilities.\n' + prompt)
    last = output / f'{task["id"]}-{arm}.final.txt'
    command = [codex, 'exec', '--json', '--skip-git-repo-check', '-C', str(work), '--output-last-message', str(last), prompt]
    start = time.monotonic()
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=timeout, env={**os.environ, 'CODEX_DISABLE_UPDATE_CHECK': '1'})
        raw, rc = done.stdout, done.returncode
        error = done.stderr
    except subprocess.TimeoutExpired as exc:
        raw = (exc.stdout or b'').decode(errors='replace') if isinstance(exc.stdout, bytes) else exc.stdout or ''
        error, rc = 'timeout', 124
    elapsed = round(time.monotonic() - start, 3)
    (output / f'{task["id"]}-{arm}.jsonl').write_text(raw)
    (output / f'{task["id"]}-{arm}.stderr.txt').write_text(error)
    events = parse_events(raw)
    after = snapshot(work)
    changed = sorted(p for p in set(baseline) | set(after) if baseline.get(p) != after.get(p))
    check = subprocess.run(task['verification'], cwd=work, capture_output=True, text=True, timeout=30)
    (output / f'{task["id"]}-{arm}.check.txt').write_text(check.stdout + check.stderr)
    usage = [node.get('usage') for event in events for node in walk(event) if isinstance(node.get('usage'), dict)]
    record = {'task': task['id'], 'arm': arm, 'fixture_sha256': baseline, 'prompt': prompt, 'command': command[:-1] + ['<prompt in record>'], 'exit_code': rc,
              'duration_seconds': elapsed, 'usage': usage[-1] if usage else None, 'cost': None, 'changed': changed,
              'verification': {'command': task['verification'], 'passed': check.returncode == 0, 'exit_code': check.returncode},
              'final': last.read_text() if last.exists() else '', 'events': events}
    record.update(score(record, task))
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--codex', default='codex')
    parser.add_argument('--timeout', type=int, default=600)
    parser.add_argument('--replay', type=Path, help='score recorded JSON without invoking a model')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.replay:
        records = json.loads(args.replay.read_text())['runs']
        for record in records:
            record.update(score(record, next(t for t in TASKS if t['id'] == record['task'])))
        mode = 'replay'
    else:
        if not shutil.which(args.codex):
            parser.error(f'{args.codex} not found; install/authenticate Codex CLI or use --replay')
        records = [run_one(t, arm, args.output, args.codex, args.timeout) for t in TASKS for arm in ('disabled', 'enabled')]
        mode = 'live'
    result = {'schema_version': 1, 'mode': mode, 'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'runs': records}
    (args.output / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps([{'task': r['task'], 'arm': r['arm'], 'score': r['score'], 'metrics': r['metrics']} for r in records], indent=2))


if __name__ == '__main__':
    main()
