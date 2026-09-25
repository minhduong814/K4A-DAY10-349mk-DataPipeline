# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm / Hình thức:** `Solo (Thực hiện độc lập - Đã được Lab Coach phê duyệt)`
- **Mã Nhóm / Lớp:** `K4-L3A-DAY10`
- **Tên Repository Nộp Bài:** `minhduong814/K4A-DAY10-GroupXX-349mk`

---

## # Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Minh Dương (Nguyễn Minh Dương) | [MSSV của bạn] | minhduong814814@gmail.com | Toàn bộ các vai trò (Pipeline Integrator, Ingestion & Cleaning, Vector Index & RAG, Observability & Evaluation) | `report/individual_report.md` |

> *Ghi chú:* Học viên thực hiện độc lập bài lab theo sự đồng ý của Lab Coach, trực tiếp thiết kế, lập trình và kiểm thử toàn bộ các module từ Ingestion đến RAG Observability.

---

## # Cá nhân

### ## MinhDuong-[MSSV]
- **Vai trò:** Solo Developer & Full-Pipeline Owner.
- **Công việc chi tiết đã hoàn thành:**
  - **Môi trường & Kiến trúc:** Cấu hình hệ sinh thái Python, quản trị secret an toàn (`.env`), thiết lập các đường dẫn artifact trong `src/core/config.py` và `src/core/utils.py`.
  - **Ingestion & Data Lineage:** Phát triển `src/ingestion/crossref.py` với khả năng parse metadata học thuật từ Crossref REST API, bóc tách thẻ JATS XML, và triển khai cơ chế offline snapshot fallback để đảm bảo pipeline chạy ổn định khi mất mạng.
  - **Cleaning & Data Modeling:** Xây dựng `src/ingestion/cleaning.py` chuẩn hóa text, tính `age_days = (run_date - published).days`, tạo trường đa ngữ cảnh 5 thành phần `text_for_embedding`, khử trùng lặp theo `paper_id`.
  - **Embedding & Vector Storage:** Phát triển `src/retrieval/embeddings.py` với kiến trúc Dual-Engine hỗ trợ cả Google Generative AI Embeddings (`models/gemini-embedding-001` / `models/text-embedding-004`) và `all-MiniLM-L6-v2`; quản lý 3 ChromaDB collections (`papers-baseline`, `papers-corrupted`, `papers-repaired`) trong `src/retrieval/index.py`.
  - **Observability Gate:** Cài đặt chốt kiểm định chất lượng tự động chuẩn Great Expectations 1.x (Ephemeral Context, 4 expectations cốt lõi) và hệ thống cảnh báo Freshness SLA (> 180 ngày) trong `src/observability/quality.py`.
  - **Evaluation & Benchmarking:** Sinh bộ test set chuẩn hóa 10 câu hỏi qua 4 nhóm nghiệp vụ (`summary`, `authors`, `date`, `categories`) trong `src/evaluation/testset.py`; đo lường Hit Rate, Token F1, LLM Judge Score trong `src/evaluation/metrics.py`.
  - **Corruption Suite & Idempotent Repair:** Triển khai 6 kịch bản tiêm lỗi dữ liệu trong `src/ingestion/corruption.py`, ghi nhận hiện tượng Silent Failure trên RAG Agent; thiết kế luồng tự phục hồi Idempotent Repair từ tầng raw backup để khôi phục 100% phong độ ban đầu trong `src/pipelines/corruption_flow.py`.
  - **Reporting & Visualization:** Tự động xuất báo cáo đối chiếu định lượng 3 trạng thái trong `src/observability/reporting.py` và hoàn thiện toàn bộ hệ thống tài liệu.
- **Điều học được / Đóng góp chính:**
  - Nắm vững kiến trúc dữ liệu hiện đại cho AI: Data Observability Gate là tấm lá chắn sống còn trước khi nạp dữ liệu vào Vector DB.
  - Hiểu rõ cơ chế "Lỗi thầm lặng" (Silent Failure): Dữ liệu bẩn không làm crash code nhưng làm AI suy giảm độ chính xác và gây ảo giác.
  - Thiết kế Idempotent Pipeline dựa trên Raw Preservation: Luôn lưu trữ nguyên vẹn dữ liệu thô ban đầu để hệ thống có năng lực tự chữa lành (Self-Healing) khi gặp sự cố.
