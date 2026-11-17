"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, aggregate, load_spec, per_item
from lab9.graders import GRADERS


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    problems = []
    graded = [m['id'] for m in spec['metrics'] if m['id'] in GRADERS]
    pairs = []
    tags = []
    for name, report in (("PR", pr), ("baseline", base)):
        rows, manifest, metrics = report.get('rows', []), report.get('manifest', {}), report.get('metrics', {})
        seeds = manifest.get('seeds', [])
        keys = [(r.get('item_id'), r.get('seed')) for r in rows]
        pairs.append(set(keys))
        item_tags = {}
        if not seeds or len(set(seeds)) != len(seeds):
            problems.append(f"{name}: empty or duplicate manifest seeds")
        if len(rows) != manifest.get('items', 0) * len(seeds) or len(set(keys)) != len(rows):
            problems.append(f"{name}: missing or duplicate rows")
        items = {k[0] for k in keys}
        if len(items) != manifest.get('items') or set(keys) != {(i, s) for i in items for s in seeds}:
            problems.append(f"{name}: incomplete item x seed grid")
        if report.get('evaluator_failures'):
            problems.append(f"{name}: evaluator failures")
        for mid, value in metrics.items():
            if value is not None and (not isinstance(value, (int, float)) or not math.isfinite(value)):
                problems.append(f"{name}: nonfinite/invalid metric {mid}")
        for m in spec['metrics']:
            if m.get('blocking') and metrics.get(m['id']) is None:
                problems.append(f"{name}: missing blocking metric {m['id']}")
        valid = True
        for row in rows:
            for mid in graded:
                value = row.get(mid)
                if not isinstance(value, (int, float)) or not math.isfinite(value) or value not in (0, 1):
                    valid = False
                    problems.append(f"{name}: invalid {mid} at {row.get('item_id')}@{row.get('seed')}")
            item, slice_tags = row.get('item_id'), frozenset(row.get('slices') or [])
            if item in item_tags and item_tags[item] != slice_tags:
                problems.append(f"{name}: inconsistent slices for {item}")
            item_tags[item] = slice_tags
        tags.append(item_tags)
        # Real harness reports include cost; recompute to catch edited summary values.
        if valid and rows and all('cost' in r for r in rows):
            if any(not isinstance(r['cost'], (int, float)) or not math.isfinite(r['cost']) or r['cost'] < 0 for r in rows):
                problems.append(f"{name}: invalid cost")
            else:
                recomputed = aggregate(rows, graded, k_values=spec.get('pass_k', []))
                for mid, value in recomputed.items():
                    if metrics.get(mid) != value:
                        problems.append(f"{name}: summary differs from rows: {mid}")
    if pairs[0] != pairs[1]:
        problems.append('PR/baseline item-seed sets differ')
    if tags[0] != tags[1]:
        problems.append('PR/baseline slice tags differ')
    if spec.get('seeds') and set(pr['manifest'].get('seeds', [])) != set(spec['seeds']):
        problems.append('PR seeds differ from spec')
    if base_spec and spec.get('eval_set_version') == base_spec.get('eval_set_version'):
        for section in ('metrics', 'slices'):
            key = (lambda m: m['id']) if section == 'metrics' else (lambda m: (m['name'], m['metric']))
            current = {key(m): m for m in spec.get(section, [])}
            for old in base_spec.get(section, []):
                mid = key(old)
                if mid not in current:
                    problems.append(f'ratchet: removed {section} {mid}')
                    continue
                new = current[mid]
                if old.get('blocking') and not new.get('blocking'):
                    problems.append(f'ratchet: disabled blocking {mid}')
                a = old.get('threshold', {}) if section == 'metrics' else old
                b = new.get('threshold', {}) if section == 'metrics' else new
                for threshold in ('min', 'max', 'max_increase'):
                    if threshold in a and (threshold not in b or
                            (b[threshold] < a[threshold] if threshold == 'min' else b[threshold] > a[threshold])):
                        problems.append(f'ratchet: loosened {mid}/{threshold}')
                if a.get('no_significant_drop') and not b.get('no_significant_drop'):
                    problems.append(f'ratchet: removed no_significant_drop {mid}')
    return list(dict.fromkeys(problems))


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    bs = spec.get('bootstrap', {})
    for entry in spec.get('slices', []):
        name, metric = entry['name'], entry['metric']
        mid = f'slice:{name}/{metric}'
        a, b = per_item(pr, metric, name), per_item(base, metric, name)
        bad, note = not a or set(a) != set(b), ''
        value = sum(a.values()) / len(a) if a else None
        if value is not None and value < entry.get('min', -math.inf):
            bad = True
        if entry.get('no_significant_drop') and a and set(a) == set(b):
            keys = sorted(a)
            try:
                d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                    n_resamples=bs.get('n_resamples', 1000), rng=bs.get('rng', 2027), confidence=bs.get('confidence', 0.95))
                bad |= hi < 0
                note = f'Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]'
            except ValueError as exc:
                bad, note = True, str(exc)
        if bad and entry.get('blocking'):
            blocked.append(mid)
        lines.append(f"  {mid} {value} {note} {'BLOCK' if bad and entry.get('blocking') else 'warn' if bad else 'ok'}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                                               confidence=bs.get("confidence", 0.95))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
