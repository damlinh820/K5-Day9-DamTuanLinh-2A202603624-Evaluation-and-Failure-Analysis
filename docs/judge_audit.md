# Judge audit — replay công khai

Số liệu lấy từ lab9.judge; log tái lập nằm trong src/reports/verification.json. FAIL là lớp dương. Không sửa nhãn CSV để cải thiện điểm.

| Tiêu chí | n | κ | Precision | Recall | TP/FP/FN/TN | Floors | Quyết định |
|---|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | 24/4/6/66 | PASS | Có thể dùng cho tone trong phạm vi replay; chưa coi là chứng nhận production. |
| helpful | 100 | 0.375 | 1.000 | 0.300 | 9/0/21/70 | FAIL | Loại khỏi release gate. |

Floors: κ≥0.6, precision≥0.8, recall≥0.7. Judge helpful bỏ sót 21/30 lỗi dù precision=1: câu lịch sự có thể sai tiền. Dùng code/ledger cho tiền và phê duyệt. Kappa không xác định phải fail calibration.

Rogan–Gladen: tone observed FAIL 0.28 → corrected 0.30; helpful 0.09 → 0.30. Hiệu chỉnh prevalence không chữa recall kém và không khiến helpful đủ điều kiện dùng.

## Audit bất đồng

Đánh giá dựa trên reply và cột note của fixture; đây là audit có hỗ trợ công cụ, chưa phải vòng gắn nhãn người độc lập mới.

| Case | Judge | Người | Kết luận từ bằng chứng | Hành động rubric/nhãn |
|---|---|---|---|---|
| H-008 | PASS | FAIL | Người đúng: xưng em/nha/check quá suồng sã theo quy chuẩn fixture. | Nêu rõ mức trang trọng, thêm ví dụ gần ranh giới. |
| H-017 | PASS | FAIL | Người đúng theo note về khách lớn tuổi; reply riêng lẻ không chứa tuổi. | Cấp ngữ cảnh người nhận; không đoán tuổi từ câu chữ. |
| H-029 | PASS | FAIL | Người đúng: không cần nhắn thêm mang sắc thái ra lệnh. | Chấm cả câu, không dùng Dạ/vui lòng làm tín hiệu đủ để PASS. |
| H-042 | FAIL | PASS | Người đúng: câu ngắn đủ nội dung và lịch sự. | Không bắt buộc lời xin lỗi trong mọi phản hồi. |
| H-051 | FAIL | PASS | Người đúng theo quy định LogiX cho phép từ refund. | Thêm glossary từ được phép; không phạt mọi từ tiếng Anh. |
| H-063 | PASS | FAIL | Người đúng theo note: hứa hoàn thêm ngoài kết quả hệ thống. | Tách cam kết có căn cứ khỏi tone; yêu cầu đối chiếu ledger/policy bằng code. |
| H-070 | PASS | FAIL | Người đúng: emoji cười không phù hợp khiếu nại. | Thêm tiêu chí emoji theo ngữ cảnh. |
| H-081 | FAIL | PASS | Note của bộ dữ liệu nói người đọc nhầm ticket, judge đúng; reply đơn lẻ không đủ tự xác minh. | Đưa case đi adjudication với ticket gốc; tạo bản nhãn version mới sau duyệt, giữ CSV hiện tại. |
| H-088 | FAIL | PASS | Theo note, người chấp nhận lỗi gõ lặp Dạ. | Phân biệt lỗi gõ nhỏ với thiếu tôn trọng. |
| H-094 | PASS | FAIL | Người đúng theo yêu cầu tiếng Việt có dấu của fixture. | Thêm chuẩn ngôn ngữ, kiểm tra dấu bằng code nếu thích hợp. |
| HL-015 | PASS | FAIL | Người đúng theo note: nói 55.000, ledger 40.000. | Code kiểm tiền; không lấy văn phong làm proxy helpfulness. |

## Hạn chế và bước tiếp

CSV đã công khai; kết quả không phải held-out. Chưa có rejudge sau sửa rubric, vì vậy không tuyên bố κ tăng. Cần hai người gắn nhãn độc lập, hòa giải bất đồng rồi đánh giá trên dữ liệu mới; giữ bản gốc để so sánh và lưu lịch sử nhãn. Judge tone chỉ dùng đúng tiêu chí đã calibration, không thay code grader về tiền.
