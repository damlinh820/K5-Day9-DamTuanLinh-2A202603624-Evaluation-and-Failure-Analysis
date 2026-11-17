"""Reproduce M0-M7 evidence; expected negative gate exits count as success.

Run from src: python -m lab9.verify_submission. No reports are hand-edited.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
from lab8.console import utf8_stdio


def main():
    utf8_stdio()
    logs = []
    def run(module, *args, expected=0):
        cmd = [sys.executable, '-m', module, *args]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8',
                                env={**os.environ, 'PYTHONUTF8': '1'})
        log = {'command': 'python -m ' + ' '.join([module, *args]), 'expected_exit': expected,
               'exit': result.returncode, 'output': result.stdout + result.stderr}
        logs.append(log)
        print(log['command'], flush=True)
        print(log['output'], flush=True)
        Path('reports').mkdir(exist_ok=True)
        Path('reports/verification.json').write_text(json.dumps(logs, ensure_ascii=False, indent=2), encoding='utf-8')
        if result.returncode != expected:
            raise RuntimeError(f"unexpected exit {result.returncode}, wanted {expected}")
    run('lab9.smoke')
    run('lab9.evalset', '--check')
    run('lab9.evalset', '--v2')
    run('pytest', '-q', '-o', 'addopts=')
    run('lab9.evidence')
    run('lab9.judge', '--csv', 'data/eval/judge_tone_public.csv', '--audit', '10')
    run('lab9.judge', '--csv', 'data/eval/judge_helpful_public.csv', '--audit', '5', expected=1)
    for version in (1, 2):
        spec = 'config/metric_spec.yaml' if version == 1 else 'config/metric_spec_v2.yaml'
        base = f'reports/baseline_v{version}.json'
        run('lab9.eval', '--shape', 'swarm', '--spec', spec, '--out', base)
        run('lab9.gate', '--pr', base, '--baseline', base, '--spec', spec, '--base-spec', spec)
        shapes = ('swarm', 'fixed', 'seeded_regression') if version == 1 else ('fixed', 'honest_refactor', 'slice_regression', 'flaky_regression')
        for shape in shapes:
            out = f'reports/eval_{shape}.json' if version == 1 else f'reports/eval_{shape}_v2.json'
            run('lab9.eval', '--shape', shape, '--spec', spec, '--out', out)
            run('lab9.gate', '--pr', out, '--baseline', base, '--spec', spec, '--base-spec', spec,
                expected=1 if 'regression' in shape else 0)
        if version == 1:
            run('lab9.ci_check', '--pr', 'reports/eval_swarm.json', '--baseline', base, '--spec', spec)
            run('lab9.mutation', '--detect', '--spec', spec)
        else:
            run('lab9.mutation', '--spec', spec, '--aa', '66,77,88,99,110')
            run('lab9.mutation', '--spec', spec, '--baseline', base, '--base-spec', spec)
            run('lab9.traps', '--pr', 'reports/eval_slice_regression_v2.json', '--baseline', base, '--spec', spec)
            for trap in ('evaluator_errors_as_nan', 'dropped_failing_rows', 'cherry_picked_seeds', 'loosened_spec'):
                run('lab9.gate', '--pr', f'reports/traps/{trap}.json', '--baseline', base,
                    '--spec', f'reports/traps/{trap}.spec.yaml' if trap == 'loosened_spec' else spec,
                    '--base-spec', spec, expected=1)
    print('All submission checks passed.', flush=True)


if __name__ == '__main__':
    main()
