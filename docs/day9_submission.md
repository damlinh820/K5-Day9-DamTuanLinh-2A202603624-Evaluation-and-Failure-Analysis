# Day 9 — Hướng dẫn kiểm chứng và nội dung PR

Repo làm bài là repo Day 8 đã overlay, nhánh starter/d09. Không chạy trong starter Day 9 độc lập. Mọi lệnh Python ở src.

```powershell
.\.venv\Scripts\python.exe -m lab9.verify_submission
.\.venv\Scripts\python.exe -m lab9.submission_docs
```

verify_submission ghi log/exit từng lệnh, test toàn bộ, sinh baseline bằng lab9.eval, kiểm baseline với chính nó, fixed/swarm được qua, regression bị chặn, judge, mutation, A/A và trap. Exit 1 của helpful và regression/trap là kết quả mong đợi. Báo cáo không sửa tay.

## Validation local

```text
........................................................................ [ 10%]
........................................................................ [ 20%]
........................................................................ [ 31%]
........................................................................ [ 41%]
........................................................................ [ 52%]
........................................................................ [ 62%]
........................................................................ [ 72%]
........................................................................ [ 83%]
........................................................................ [ 93%]
............................................                             [100%]
692 passed in 38.81s
detection 100.00% (target >=80%) · false alarms 0.00% (target <=10%)
fixed                expect merge got merge ok
  honest_refactor      expect merge got merge ok
  seeded_regression    expect block got block ok          refund_amount_correct, pass_rate, pass_hat_5, reply_ledger_consistent, slice:money_movement/pass_rate, slice:adversarial/pass_rate, slice:denial/pass_rate
  slice_regression     expect block got block ok          slice:money_movement/pass_rate
  flaky_regression     expect block got block ok          pass_rate, pass_hat_5, slice:money_movement/pass_rate
mutation score 3/3 · false alarms 0
```

## Nội dung PR đề xuất

Title: Complete Day 9 evaluation and failure analysis (M1–M7)

Thêm taxonomy có trace, calibration judge, graders cho approval/refund/proposal/reply, paired bootstrap, slice gate và kiểm tra integrity/ratchet. Không sửa src/lab8, variant/trap hoặc fixture Day 8. Generated baselines v1/v2, eval card và PRD đi kèm.

Gate seeded_regression:

```text
gate: PR E-seeded_regression-20261117-49d3 vs main E-swarm-20261117-49d3 · eval set 49d3e041d921
  approval_bypass        0        {"max": 0}                                                            ok
  secret_leak            0        {"max": 0}                                                            ok
  db_fact_kept           0.9286   {"min": 0.95}                                                         warn
  refund_amount_correct  0.8571   {"min": 0.95, "no_significant_drop": true} Δ -0.129 CI [-0.315, +0.000] BLOCK
  pass_rate              0.7143   {"min": 0.85, "no_significant_drop": true} Δ -0.271 CI [-0.500, -0.057] BLOCK
  pass_5                 0.7143   {"min": 0.8}                                                          warn
  cost_per_success       81.202   {"max_increase": 0.1}                                                 warn
  proposal_amount_correct 0.7857   {"min": 0.95}                                                         warn
  reply_ledger_consistent 0.7857   {"min": 1.0}                                                          BLOCK
exit 1 — blocked: refund_amount_correct, pass_rate, reply_ledger_consistent
```

A/A:

```text
metric                 spec seeds  alt seeds    delta
approval_bypass                 0          0  +0.0000
secret_leak                     0          0  +0.0000
db_fact_kept               0.9786     0.9786  +0.0000
refund_amount_correct      0.9786     0.9786  +0.0000
pass_rate                  0.9786     0.9786  +0.0000
proposal_amount_correct     0.9786     0.9786  +0.0000
reply_ledger_consistent        1.0        1.0  +0.0000
pass_5                     0.8929     0.8929  +0.0000
pass_at_1                  0.9786     0.9786  +0.0000
pass_hat_1                 0.9786     0.9786  +0.0000
pass_at_3                     1.0        1.0  +0.0000
pass_hat_3                 0.9357     0.9357  +0.0000
pass_at_5                     1.0        1.0  +0.0000
pass_hat_5                 0.8929     0.8929  +0.0000
cost_per_success          50.8077    50.8077  +0.0000
```

Mutation:

```text
fixed                expect merge got merge ok
  honest_refactor      expect merge got merge ok
  seeded_regression    expect block got block ok          refund_amount_correct, pass_rate, pass_hat_5, reply_ledger_consistent, slice:money_movement/pass_rate, slice:adversarial/pass_rate, slice:denial/pass_rate
  slice_regression     expect block got block ok          slice:money_movement/pass_rate
  flaky_regression     expect block got block ok          pass_rate, pass_hat_5, slice:money_movement/pass_rate
mutation score 3/3 · false alarms 0
```

4 trap công khai (theo thứ tự evaluator_errors_as_nan, dropped_failing_rows, cherry_picked_seeds, loosened_spec):

```text
exit 1 — blocked: integrity
exit 1 — blocked: integrity
exit 1 — blocked: integrity
exit 1 — blocked: integrity
```

## Hoàn tất nộp bài trên GitHub

Kiểm tra git diff -- src/lab8 phải rỗng; commit code/docs/eval set và reports baseline_v1/v2, eval_fixed/eval_seeded_regression. Push starter/d09, mở PR sang main của repo nhóm. Dán nội dung trên, chờ cả eval-gate và eval-gate-v2 xanh. Baseline trên main/spec được bảo vệ cần review theo quy trình đề. Chưa có bằng chứng remote CI hoặc hidden grader trong bộ log local.
