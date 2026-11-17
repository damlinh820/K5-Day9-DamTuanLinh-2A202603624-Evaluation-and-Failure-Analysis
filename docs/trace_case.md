# Trace case — FM-03: ticket đè dữ kiện DB

| Trường | Nội dung |
|---|---|
| Trial | seeded_regression C-002@11, trace run ID R-seeded_regression-C-002-s11; report src/reports/eval_seeded_regression.json |
| Triệu chứng | RefundAmountCorrect và DbFactKept fail; ledger ghi 20.000đ, nhãn yêu cầu 0/denied. Reply xác nhận 20.000đ nên riêng metric FM-08 không bắt lỗi này. |
| Bước sai đầu tiên | Event 3, model_override, payload {delay_days: 5}. |
| Vì sao đầu tiên | Event 1 handoff chỉ cho tool đọc; event 2 investigator trả order visible=true, delay_days=2. Dữ kiện đúng đã có trước khi bị thay thế. |
| Failure mode | FM-03 ticket_trust, layer model/prompt. |
| Hậu quả | Event 4 quote 20.000; host ghi refund; event 5 refund_history chỉ đọc; event 6 reply nói đã hoàn 20.000. |
| Đối chứng | fixed C-002@11 không có override; event 3 quote=0; status denied, ledger=0. |
| Regression test | tests/test_lab9_regressions.py::test_ticket_override_first_wrong_step xác minh DB, event đầu sai, ledger và hai grader trên cả variant lỗi/fixed. |
| Chưa chắc chắn | Trace không chứng minh suy nghĩ nội bộ của model; seed cố định không đại diện LLM thật. Host cho phép khoản tiền trong giới hạn approval, không thay thế kiểm chứng entitlement ở shape. |

Tái lập từ src:

```powershell
.\.venv\Scripts\python.exe -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
.\.venv\Scripts\python.exe -m lab9.trace_case --shape fixed --claim C-002 --seed 11
.\.venv\Scripts\python.exe -m pytest -q -m student -o addopts= -k ticket_override_first_wrong_step
```

Test kỳ vọng grader từ chối bản lỗi và chấp nhận fixed; không sửa agent bị khóa để làm test xanh.
