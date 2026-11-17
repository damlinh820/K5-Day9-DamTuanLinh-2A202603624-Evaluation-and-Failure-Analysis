"""Reproduce trace evidence without editing any supplied variant or Lab 8 file.

Run from src: python -m lab9.evidence. Writes machine-generated evidence only.
"""
from pathlib import Path
import json
import tempfile
from types import SimpleNamespace

from lab8.shapes import SHAPES
from lab8.console import utf8_stdio
from lab9 import variants
from lab9.eval import load_spec, load_world, make_task
from lab9.graders import GRADERS
from lab9.variant_agent import make_shape


CASES = [
    ('FM-01', 'leaky_trace', 'C-001'), ('FM-02', 'ignore_denied', 'C-007'),
    ('FM-03', 'ticket_trust', 'C-002'), ('FM-04', 'sum_parts', 'C-014'),
    ('FM-05', 'pre_deducted', 'C-014'), ('FM-06', 'stale_clause', 'C-006'),
    ('FM-07', 'sibling_refund', 'C-001'), ('FM-08', 'misreport', 'C-014'),
    ('FM-09', 'no_override', 'C-005'),
]


def collect():
    variants.register()
    spec = load_spec(Path('config/metric_spec_v2.yaml'))
    world, claims = load_world(spec)
    labels = {c['claim_id']: c['expected'] for c in claims}
    records = []
    for fm, switch, cid in CASES:
        name = 'evidence_' + switch
        SHAPES[name] = make_shape(name, {'no_override', switch})
        for shape in (name, 'fixed'):
            with tempfile.TemporaryDirectory(prefix='lab9-evidence-', ignore_cleanup_errors=True) as tmp:
                trial = make_task(shape, world, claims, labels, Path(tmp))({'claim_id': cid, 'seed': 11})
            ctx = SimpleNamespace(output=trial, expected_output=labels[cid])
            scores = {mid: {'value': g().evaluate(ctx).value, 'reason': g().evaluate(ctx).reason}
                      for mid, g in GRADERS.items()}
            if scores['secret_leak']['value']:
                scores['secret_leak']['reason'] = 'forbidden fixture substring detected (redacted)'
            events = []
            for i, event in enumerate(trial['events'], 1):
                payload = event.get('payload')
                # Deliberate leaking variants contain fixture secrets. Keep only field names.
                if event['kind'] == 'debug_claim_row':
                    payload = {'redacted_fields': sorted(payload)}
                events.append({'step': i, 'kind': event['kind'], 'payload': payload})
            records.append({'fm': fm, 'shape': shape, 'claim_id': cid, 'seed': 11,
                            'run_id': trial['result']['run_id'], 'status': trial['result']['status'],
                            'ledger': trial['snapshot'], 'unexpected_rows': trial['unexpected_rows'],
                            'scores': scores, 'events': events})
    return records


def main():
    utf8_stdio()
    records = collect()
    out = Path('reports/trace_evidence.json')
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
    for r in records:
        print(r['fm'], r['shape'], r['claim_id'], r['status'], r['ledger']['refund_vnd'],
              'failed:', [m for m, v in r['scores'].items() if v['value'] == (m in ('secret_leak', 'approval_bypass'))])
        if r['shape'] != 'fixed':
            for e in r['events']:
                if e['kind'] not in ('handoff', 'investigator'):
                    print(' ', e)
    print('wrote', out)


if __name__ == '__main__':
    main()
