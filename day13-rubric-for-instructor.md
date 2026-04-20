# Rubric chấm điểm giảng viên - Day 13 Observability Lab

## Mục tiêu chấm
Rubric này áp dụng mô hình **60/40**:
- **60 điểm Nhóm**: Đánh giá qua demo live và kết quả triển khai kỹ thuật (Logs, Traces, Dashboard, Alerts).
- **40 điểm Cá nhân**: Đánh giá qua báo cáo phần việc tự làm, bằng chứng commit/PR, và khả năng trả lời câu hỏi trực tiếp.

---

## A. Group Score (Điểm Nhóm) - 60 điểm

### A1. Implementation Quality (Triển khai kỹ thuật) - 30 điểm
- **10đ - Logging & Tracing**: JSON schema đúng, có correlation ID xuyên suốt, có ít nhất 10 traces trên Langfuse với đầy đủ metadata.
- **10đ - Dashboard & SLO**: Dashboard 6 panels rõ ràng, có đơn vị, có threshold/SLO line. Có bảng SLO hợp lý.
- **10đ - Alerts & PII**: PII được redact hoàn toàn. Có ít nhất 3 alert rules với runbook link hoạt động.

### A2. Incident Response & Debugging - 10 điểm
- Xác định đúng root cause của incident đã inject.
- Giải thích được flow: Metrics -> Traces -> Logs để tìm ra nguyên nhân.

### A3. Live Demo & Communication - 20 điểm
- App chạy mượt mà, không lỗi runtime bất ngờ.
- Nhóm trình bày tự tin, rõ ràng, đúng thuật ngữ chuyên môn.
- Giải thích được logic của middleware và logging pipeline.

---

## B. Individual Score (Điểm Cá nhân) - 40 điểm

### B1. Individual Report & Quality - 20 điểm
- Phần báo cáo cá nhân trong `blueprint-template.md` chi tiết, rõ ràng.
- Hiểu sâu về phần việc mình đảm nhận (ví dụ: giải thích được regex PII hoặc cách tính P95).

### B2. Evidence of Work (Commit/PR) - 20 điểm
- Có bằng chứng đóng góp code cụ thể qua Git (Commits/PRs).
- Tham gia vào quá trình demo phần mình phụ trách (trả lời được câu hỏi hóc búa của giảng viên).

---

## C. Bonus (Tối đa 10 điểm)
- **+3đ**: Tối ưu chi phí (số liệu trước/sau).
- **+3đ**: Dashboard đẹp, chuyên nghiệp vượt mong đợi.
- **+2đ**: Tự động hóa (Auto-instrumentation hoặc script custom).
- **+2đ**: Có Audit logs tách riêng.

---

## Điều kiện đạt (Passing Criteria)
- VALIDATE_LOGS_SCORE đạt ít nhất 80/100.
- Có ít nhất 10 traces live.
- Có dashboard đủ 6 panels.
- Có blueprint report đầy đủ tên thành viên.

---

## Phiếu chấm nhanh
| Hạng mục | Điểm tối đa | Điểm đạt |
|---|---:|---:|
| **GROUP (60%)** | **60** | |
| - Implementation | 30 | |
| - Incident Debug | 10 | |
| - Live Demo | 20 | |
| **INDIVIDUAL (40%)** | **40** | |
| - Individual Report | 20 | |
| - Git Evidence | 20 | |
| **Bonus** | 10 | |
| **TỔNG** | **100+** | |
