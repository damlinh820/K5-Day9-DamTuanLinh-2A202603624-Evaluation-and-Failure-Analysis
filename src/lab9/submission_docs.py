"""Build numeric documentation from generated reports (never modify reports)."""
from pathlib import Path
import hashlib
import json
import subprocess
from lab9.eval import load_spec, per_item
from lab9.gate import check
from lab9.judge import calibrate
from lab9.stats import paired_bootstrap


def read(name):
    return json.loads(Path('reports', name + '.json').read_text(encoding='utf-8'))


def write_doc(path, content):
    path.write_text('\n'.join(line.rstrip() for line in content.splitlines()) + '\n', encoding='utf-8')


def main():
    docs = Path('../docs')
    b1, b2 = read('baseline_v1'), read('baseline_v2')
    spec1, spec2 = load_spec(), load_spec(Path('config/metric_spec_v2.yaml'))
    verification = read('verification')
    if any(r['exit'] != r['expected_exit'] for r in verification):
        raise RuntimeError('finish verification before producing submission docs')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    source_files = sorted([*Path('lab9').glob('*.py'), *Path('config').glob('*spec*.yaml'), Path('config/fm_map.yaml')])
    fingerprint = hashlib.sha256(b''.join(str(p).encode() + p.read_bytes() for p in source_files)).hexdigest()
    runs = [(1, b1), (1, read('eval_fixed')), (1, read('eval_seeded_regression')),
            (2, b2), *[(2, read('eval_' + s + '_v2')) for s in ('fixed', 'honest_refactor', 'slice_regression', 'flaky_regression')]]
    table = ['| Set | Run ID | Pass rate | Refund correct | Reply consistent | pass^5 | Gate |',
             '|---|---|---:|---:|---:|---:|---|']
    cis = []
    for v, r in runs:
        base, spec = (b1, spec1) if v == 1 else (b2, spec2)
        blocked, _ = check(r, base, spec, spec)
        m = r['metrics']
        table.append(f"| v{v} | {r['run_id']} | {m['pass_rate']} | {m['refund_amount_correct']} | {m['reply_ledger_consistent']} | {m.get('pass_hat_5', m['pass_5'])} | {'BLOCK: ' + ', '.join(blocked) if blocked else 'MERGE'} |")
        a, b = per_item(r, 'pass_rate'), per_item(base, 'pass_rate')
        keys = sorted(a)
        d, lo, hi = paired_bootstrap([a[k] for k in keys], [b[k] for k in keys])
        cis.append(f"- {r['run_id']}: Δ={d:+.6f}, CI95%=[{lo:+.6f}, {hi:+.6f}].")
    threshold_table = ['| Metric | Loại | Ngưỡng v1 | Blocking | Baseline v1 |', '|---|---|---|---|---:|']
    for m in spec1['metrics']:
        threshold_table.append(f"| {m['id']} | {m['kind']} | `{json.dumps(m.get('threshold', {}))}` | {m.get('blocking', False)} | {b1['metrics'].get(m['id'])} |")
    judge_lines = []
    for kind in ('tone', 'helpful'):
        j = calibrate(Path(f'data/eval/judge_{kind}_public.csv'))
        judge_lines.append(f"- {kind}: n={j['n']}, κ={j['kappa']}, P={j['precision']}, R={j['recall']}, floors={'PASS' if j['passed'] else 'FAIL'}; confusion={j['confusion']}.")
    aa = next(x['output'] for x in verification if '--aa ' in x['command'])
    mutation = next(x['output'] for x in verification if x['command'].startswith('python -m lab9.mutation') and '--baseline' in x['command'])
    detection = next(x['output'] for x in verification if '--detect' in x['command'])
    tests = next(x['output'] for x in verification if x['command'].startswith('python -m pytest'))
    gate_output = next(x['output'] for x in verification if x['command'].startswith('python -m lab9.gate --pr reports/eval_seeded_regression'))
    limitations = '''- MockLLM, fixture giả và judge replay công khai; chưa đo người dùng/model thật hoặc held-out.
- v1 14 item, v2 28 item; seed không phải mẫu độc lập giữa các item. Bootstrap resample item đã lấy mean qua seed, không coi 70/140 trial là độc lập.
- Bug rare chỉ bật seed chia hết cho 3: bộ 5 seed hiện tại có một seed kích hoạt. Không bảo đảm phát hiện mọi lỗi xác suất 1/3 với cỡ mẫu nhỏ; không chỉnh sàn tới khi bắt được mẫu ẩn.
- Swarm Day 8 không có event reply. FM-08=1 ở baseline nghĩa là không có phát biểu để đối chiếu, không chứng minh chất lượng reply. Variant có reply được kiểm thật. Parser hiện hỗ trợ số nguyên VND và các ký hiệu đ/đồng/VND/₫; không hiểu mọi phát biểu bằng chữ hay ngữ cảnh hứa hoàn tiền tương lai.
- FM-09 mới có bằng chứng guardrail chặn truy cập; chưa quan sát bypass thành công. Key 5 anchor và grader ẩn của giảng viên không có trong starter.
- Gate chống report thiếu dòng/seed, trùng dòng, NaN, grader lỗi, sửa aggregate và đổi slice so với baseline. Nó không thay chữ ký nguồn dữ liệu hay bảo vệ CI: baseline/spec phải lấy từ nhánh được bảo vệ.
- Các baseline được sinh tại nhánh starter/d09 với swarm giữ nguyên; chưa được phê duyệt trên main. CI GitHub và PR chưa được xác nhận bởi lần kiểm chứng local này.
'''
    card = f'''# Eval card — Day 9

Tài liệu sinh bằng `python -m lab9.submission_docs` từ reports; không sửa tay report.

- Chủ sở hữu gate: Đàm Tuấn Linh (implementation/evaluation).
- Commit nền khi sinh bằng chứng: `{commit}`; code Day 9 là working tree đi kèm, fingerprint SHA256 `{fingerprint}`. Khi nộp dùng commit chứa các file này; không coi commit nền là phiên bản code hoàn thiện.
- v1 SHA: `{b1['manifest']['eval_set_sha']}`; v2 SHA: `{b2['manifest']['eval_set_sha']}`.
- Spec v1={spec1['metric_spec_version']}; spec v2={spec2['metric_spec_version']}; seeds={spec1['seeds']}; bootstrap percentile, paired=True, 1000 resample, RNG 2027, CI95%.
- Nhãn tách tại labels_v1.json / labels_v2.json, nguồn public Lab 8 và adversarial instructor; mapping/provenance đi kèm từng item.

## Kết quả và gate

{chr(10).join(table)}

## Paired bootstrap pass_rate so với baseline cùng version

{chr(10).join(cis)}

## Ngưỡng v1

{chr(10).join(threshold_table)}

Safety là số vi phạm, max=0; không lấy trung bình để che lỗi. ProposalAmountCorrect là metric chẩn đoán FM-05 khi ledger=0 nhưng đề xuất bị trừ sai, không dùng để nới gate.

## Judge và khả năng giải thích lỗi

{chr(10).join(judge_lines)}

```text
{detection.strip()}
```

Xem [judge audit](judge_audit.md), [taxonomy](failure_taxonomy.md) và [trace case](trace_case.md). Regression test xác minh event 3 model_override trên C-002@11, đối chứng fixed.

## v2: slice, độ ổn định và A/A

pass_hat_5 blocking min={next(m['threshold']['min'] for m in spec2['metrics'] if m['id']=='pass_hat_5')}. Sàn giữ ở 0.80 theo yêu cầu rubric, thấp hơn mức baseline/A-A đo được; không hạ sàn để hợp thức hóa regression. Money_movement min=0.95, adversarial min=0.90, denial min=0.90; tất cả blocking và không giảm có ý nghĩa. Threshold này áp dụng version v2 mới, không nới v1.

```text
{aa.strip()}
```

A/A bằng 0 trên hai bộ seed của MockLLM, không suy ra LLM thật không có nhiễu. Với LLM thật cần nhiều lần đo và chọn sàn ngoài dải nhiễu trước khi thử PR. Không dùng A/A khác seed như PR gate vì integrity yêu cầu cùng item/seed.

```text
{mutation.strip()}
```

## Pilot và giới hạn

Chỉ pilot offline cho claim hoàn phí/bồi thường một đơn trong fixture LogiX, qua approval và trần của host. Chưa cho phép tiền thật. Ngoài phạm vi: nhiều đơn, tranh chấp pháp lý, currency khác, chính sách mới chưa có nhãn.

{limitations}

Tăng eval-set version khi thêm/đổi item hoặc nhãn; sinh lại baseline, review provenance và ngưỡng. Đổi grader/spec cần version và lý do; cùng eval-set version chỉ được siết. Khi gate exit 1, owner phân tích trace và thêm regression test trước khi đề xuất merge.
'''
    write_doc(docs / 'eval_card.md', card)
    prd = f'''# PRD v1.1 — Bổ sung đánh giá cho LogiX-VN

## 1. Thay đổi

Giữ nguyên tính năng/host/agent Lab 8. Thêm tiêu chí có thể đo, evidence tái lập và cổng chặn regression. Thay demo thủ công bằng eval set, code graders, bootstrap và gate. Code nằm trong lab9; bổ sung section eval vào harness_map theo đề.

## 2. Phạm vi pilot

Pilot offline với claim một đơn trong fixture, tiền VND, giới hạn theo approval và policy/trần đơn do host Lab 8 quyết định. Không triển khai tiền thật; ngoài phạm vi nhiều đơn, tranh chấp pháp lý và chính sách mới. Môi trường đo MockLLM: v1 {b1['manifest']['items']} item × {len(b1['manifest']['seeds'])} seed, v2 {b2['manifest']['items']} item × {len(b2['manifest']['seeds'])} seed.

## 3. Định nghĩa chạy đúng

Baseline `{b1['run_id']}`, SHA `{b1['manifest']['eval_set_sha']}`.

{chr(10).join(threshold_table)}

CI95% của PR − baseline hoàn toàn dưới 0 nghĩa là giảm có ý nghĩa. Dùng cặp per-item mean cùng seed, không trộn item. v2 thêm pass_hat_5≥0.80 và slice blocking; chi tiết kết quả/ngưỡng ở [eval card](eval_card.md).

## 4. Failure mode → grader

| FM | Grader | Loại và lý do |
|---|---|---|
| FM-01, FM-09 | SecretLeak + TrialPass | Code, đối chiếu trường cấm và trạng thái guardrail |
| FM-02 | TrialPass + ReplyLedgerConsistent | Code, host có thể chặn tiền nhưng agent vẫn báo thành công |
| FM-03 | DbFactKept + RefundAmountCorrect | Code, kiểm cả event lẫn ledger để tránh bỏ sót quiet override |
| FM-04, FM-06 | RefundAmountCorrect | Code, so ledger với nhãn entitlement |
| FM-05 | RefundAmountCorrect + ProposalAmountCorrect | Code, ledger đúng không có nghĩa proposal đúng |
| FM-07 | ApprovalBypass | Code, phát hiện dòng ledger ngoài claim |
| FM-08 | ReplyLedgerConsistent | Code, đối chiếu số tiền trong reply với ledger |

Tiền/approval không giao cho judge. Judge tone đạt floors nhưng chưa có held-out mới; helpful bị loại. Xem audit cho các bất đồng và đề xuất rubric, không sửa CSV gốc.

## 5. Cổng release và trách nhiệm

Đàm Tuấn Linh là eval owner theo TEAM.md. Gate exit 1 → không merge; phân tích trace, sửa phần Day 9 hoặc đề xuất thay đổi agent ở bài sau, chạy lại toàn bộ evidence. Không nới threshold cùng version để làm xanh. Baseline và base-spec cho PR phải được review trên nhánh được bảo vệ.

```text
python -m lab9.gate --pr reports/eval_fixed.json --baseline reports/baseline_v1.json --spec config/metric_spec.yaml --base-spec <spec-tu-nhanh-main>
```

Local đã kiểm bằng verify_submission; trạng thái GitHub Actions không được suy ra từ kết quả local. Không tự cấp waiver. Mọi ngoại lệ cần coach/reviewer duyệt và ghi lý do, phạm vi, ngày hết hạn trong PR; safety không được bỏ qua để cho tiền thật chạy.

## 6. Bằng chứng và rủi ro mở

{limitations}

## 7. Khi nào lên v1.2

Thêm dữ liệu thật/nhãn held-out, mở rộng ngôn ngữ reply, hoặc đổi policy/metric phải có version mới, baseline mới và review tác động. Không sửa tay report.

## Phê duyệt

| Vai trò | Người phụ trách | Trạng thái |
|---|---|---|
| Product/reviewer | Coach hoặc người review PR | Chờ review; chưa ký duyệt |
| Eval owner | Đàm Tuấn Linh | Bản chuẩn bị để chủ repo kiểm tra và nộp |
'''
    write_doc(docs / 'PRD_v1.1.md', prd)
    trap_lines = [line for x in verification if '--pr reports/traps/' in x['command']
                  for line in x['output'].splitlines() if line.startswith('exit 1')]
    submission = f'''# Day 9 — Hướng dẫn kiểm chứng và nội dung PR

Repo làm bài là repo Day 8 đã overlay, nhánh starter/d09. Không chạy trong starter Day 9 độc lập. Mọi lệnh Python ở src.

```powershell
.\.venv\Scripts\python.exe -m lab9.verify_submission
.\.venv\Scripts\python.exe -m lab9.submission_docs
```

verify_submission ghi log/exit từng lệnh, test toàn bộ, sinh baseline bằng lab9.eval, kiểm baseline với chính nó, fixed/swarm được qua, regression bị chặn, judge, mutation, A/A và trap. Exit 1 của helpful và regression/trap là kết quả mong đợi. Báo cáo không sửa tay.

## Validation local

```text
{tests.strip()}
{detection.strip()}
{mutation.strip()}
```

## Nội dung PR đề xuất

Title: Complete Day 9 evaluation and failure analysis (M1–M7)

Thêm taxonomy có trace, calibration judge, graders cho approval/refund/proposal/reply, paired bootstrap, slice gate và kiểm tra integrity/ratchet. Không sửa src/lab8, variant/trap hoặc fixture Day 8. Generated baselines v1/v2, eval card và PRD đi kèm.

Gate seeded_regression:

```text
{gate_output.strip()}
```

A/A:

```text
{aa.strip()}
```

Mutation:

```text
{mutation.strip()}
```

4 trap công khai (theo thứ tự evaluator_errors_as_nan, dropped_failing_rows, cherry_picked_seeds, loosened_spec):

```text
{chr(10).join(trap_lines)}
```

## Hoàn tất nộp bài trên GitHub

Kiểm tra git diff -- src/lab8 phải rỗng; commit code/docs/eval set và reports baseline_v1/v2, eval_fixed/eval_seeded_regression. Push starter/d09, mở PR sang main của repo nhóm. Dán nội dung trên, chờ cả eval-gate và eval-gate-v2 xanh. Baseline trên main/spec được bảo vệ cần review theo quy trình đề. Chưa có bằng chứng remote CI hoặc hidden grader trong bộ log local.
'''
    write_doc(docs / 'day9_submission.md', submission)
    print('wrote docs/eval_card.md, PRD_v1.1.md, day9_submission.md from reports')


if __name__ == '__main__':
    main()
