# Group Report — Day 10: Data Pipeline & Data Observability

> Báo cáo tổng kết toàn diện bài thực hành Day 10. Bài làm được thực hiện độc lập (Solo) bởi học viên Minh Dương (đa được phê duyệt bởi Lab Coach), đảm nhiệm toàn bộ các giai đoạn từ Ingestion, Quality Observability, Embedding, RAG Evaluation đến Corruption & Self-Healing.

---

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| :--- | :--- |
| **Khóa / Lớp** | K4 - L3A (Chương trình Đào tạo Nhân Tài AI Thực Chiến - VinUni) |
| **Tên nhóm / Hình thức** | Solo (Thực hiện độc lập — Đã được Lab Coach phê duyệt) |
| **Repository** | `https://github.com/minhduong814/K4A-DAY10-GroupXX-349mk` |
| **Ngày hoàn thành** | 2026-09-25 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Email | Vai trò chính | Module / deliverable sở hữu |
| :--: | :--- | :--- | :--- | :--- | :--- |
| 1 | Nguyễn Minh Dương | 2A202602920 | minhduong814814@gmail.com | Lead & Solo Full-Pipeline Developer | Toàn bộ dự án: `core/`, `ingestion/`, `retrieval/`, `observability/`, `evaluation/`, `pipelines/` |

---

## 2. Tóm tắt kết quả

Trong bài thực hành Day 10, tôi đã hoàn thành 100% mục tiêu từ Checkpoint 0 đến Checkpoint 5, xây dựng thành công một Data Pipeline khép kín cho hệ thống RAG Agent tích hợp trạm kiểm soát chất lượng dữ liệu tự động:

1. **Baseline Pipeline (Pha 1):** Thu thập thành công 24 bài báo học thuật từ Crossref REST API (có cơ chế offline snapshot fallback để đảm bảo tính bất biến). Dữ liệu được làm sạch, chuẩn hóa trường đa ngữ cảnh `text_for_embedding`, vượt qua 100% các tiêu chí kiểm dịch của **Great Expectations 1.x** (Ephemeral Context) và đạt chuẩn **Freshness SLA** (tỷ lệ bài quá hạn chỉ 4.2% < ngưỡng 25.0%). Dữ liệu được đánh chỉ mục vào ChromaDB và đạt kết quả đánh giá tuyệt đối trên bộ 10 câu hỏi benchmark chuẩn: **Retrieval Hit Rate = 100.0%**, **Mean Token F1 = 1.0000**, **LLM Judge Accuracy = 100.0%**.
2. **Data Corruption & Silent Failure (Pha 2):** Giả lập 6 dạng sự cố dữ liệu thực tế (bỏ rơi 20% bài mới, xóa rỗng tóm tắt, chèn nhiễu ký tự, cắt ngắn tiêu đề, lùi ngày xuất bản, nhân bản dữ liệu). Cổng kiểm soát GX 1.x đã phát hiện bất thường và kích hoạt trạng thái **FAIL (chỉ đạt 4/6 checks)**. Khi đưa dữ liệu lỗi này vào Vector DB, RAG Agent gặp hiện tượng **Lỗi thầm lặng (Silent Failure)**: Code không hề văng exception runtime nhưng hiệu năng trả lời suy giảm nghiêm trọng (**Hit Rate tụt xuống 70.0%**, **Token F1 tụt xuống 0.7000**, **Judge Accuracy tụt xuống 70.0%**).
3. **Idempotent Repair & Self-Healing:** Dựa trên nguyên tắc bảo toàn dữ liệu gốc (Raw Preservation), hệ thống tự động tái kích hoạt quy trình làm sạch từ bản sao lưu thô ban đầu, ghi đè an toàn và đưa toàn bộ chỉ số hiệu năng trở lại phong độ **100% ban đầu**.

---

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
[Crossref REST API] (với Retry & Offline Fallback)
         │
         ▼
[data/raw/crossref_response.json] & [crossref_records.json] (Raw Preservation Layer)
         │
         ▼
[Cleaning & Modeling] (Chuẩn hóa XML, tính age_days, ghép text_for_embedding, deduplicate)
         │
         ├───► [data/clean/papers_clean.csv] & [papers_clean.json]
         │
         ▼
[Data Observability Gate] (Great Expectations 1.x Ephemeral + Freshness SLA Monitoring)
         │  PASS
         ▼
[Embedding & ChromaDB Indexing] (Dual-Engine: Google Gemini Embedding / MiniLM)
         │
         ├───► Collection: papers-baseline
         │
         ▼
[Benchmark Evaluation] (10 câu hỏi đa dạng: summary, authors, date, categories)
         │
         ▼
[Synthetic Data Corruption] (Tiêm 6 kịch bản lỗi: Drop 20%, Blank, Noise, Truncate, Stale, Dups)
         │
         ├───► GX Quality Gate: Báo động FAIL
         ├───► Chroma Collection: papers-corrupted
         ├───► RAG Evaluation: Minh chứng Silent Failure (Hit Rate 100% -> 70%)
         │
         ▼
[Idempotent Repair] (Re-ingest từ Raw backup -> Re-clean -> Re-index: papers-repaired)
         │
         ▼
[Comparison & Reporting] (Bảng đối chiếu định lượng 3 trạng thái tại corruption_report.md)
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output / artifact | Owner |
| :--- | :--- | :--- | :--- | :--- |
| **Ingestion** | Crossref API / local snapshot | Fetch có timeout/retry, bóc tách metadata, khử tag HTML/XML `<jats:p>` | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Minh Dương |
| **Cleaning** | Raw `PaperRecord` objects | Chuẩn hóa whitespace, tính `age_days`, tạo `text_for_embedding`, deduplicate theo `paper_id` | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Minh Dương |
| **Observability** | Cleaned / Corrupted DataFrame | Kiểm định GX 1.x (4 expectations) & tính tỷ lệ quá hạn Freshness SLA (< 25%) | `data/quality/*_quality_report.json`, `data/quality/*freshness_report.json` | Minh Dương |
| **Embedding / Index** | Cleaned DataFrame & text tokens | Dual-Engine nhúng vector (Google Gemini Embedding / all-MiniLM-L6-v2), nạp ChromaDB Cosine HNSW | `data/chroma/`, `data/embeddings/papers_embeddings*.json` | Minh Dương |
| **Evaluation** | Cleaned DataFrame, Chroma Index | Sinh bộ đề thi 10 câu qua 4 dạng; đo Hit Rate, Token F1, LLM Judge Score | `data/eval/test_set.json`, `data/results/*_metrics.json`, `*_answers.json` | Minh Dương |
| **Corruption / Repair** | Cleaned DataFrame, Raw records | Tiêm 6 kịch bản lỗi dữ liệu; tự phục hồi từ raw backup | `data/results/corruption_log.json`, `data/clean/*_corrupted.*`, `*_repaired.*` | Minh Dương |
| **Orchestration** | Toàn bộ pipeline modules | Điều phối Phase 1 (`run_phase1.py`) và Phase 2 (`run_corruption_flow.py`) | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` | Minh Dương |

---

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến / Cấu hình | Giá trị sử dụng | Ghi chú |
| :--- | :--- | :--- |
| `LLM_PROVIDER` | `gemini` | Sử dụng Google Gemini làm LLM Judge & QA Agent |
| `LLM_MODEL` | `gemini-3.1-flash-lite` | Phản hồi siêu nhanh, độ chính xác cao |
| `EMBEDDING_PROVIDER` | `google` (hoặc auto-fallback) | Hỗ trợ Google Generative AI Embeddings (`models/gemini-embedding-001`) |
| Số lượng Crossref records | `24` | 24 bài báo học thuật chuẩn mực |
| Retrieval `top_k` | `4` | Lấy 4 ngữ cảnh liên quan nhất cho mỗi câu hỏi |
| Freshness threshold | `180` ngày | Ngưỡng xác định bài báo cũ theo SLA |
| Great Expectations Mode | `ephemeral` | Chạy trực tiếp trên RAM, không sinh file rác |

### Lệnh cài đặt

```bash
# Kích hoạt môi trường ảo
source .venv/bin/activate

# Cài đặt package liên kết
python -m pip install -e .
```

### Lệnh chạy thực nghiệm

1. **Chạy Baseline Pipeline (Pha 1):**
   ```bash
   python script/run_phase1.py
   ```
2. **Chạy Corruption & Repair Flow (Pha 2):**
   ```bash
   python script/run_corruption_flow.py
   ```

### Kết quả tái hiện thực tế

| Lệnh | Trạng thái | Thời điểm chạy | Bằng chứng artifact |
| :--- | :---: | :---: | :--- |
| `python script/run_phase1.py` | Thành công 100% | 2026-09-25 | `data/clean/papers_clean.json`, `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| `python script/run_corruption_flow.py` | Thành công 100% | 2026-09-25 | `data/results/corruption_log.json`, `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`, `data/reports/corruption_report.md` |

---

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị thực tế |
| :--- | :--- |
| **Source API** | Crossref REST API (`https://api.crossref.org/works`) |
| **Query / Filter** | `query=agentic retrieval augmented generation large language model`, `filter=from-pub-date:2026-03-29,has-abstract:true` |
| **Số records nhận được** | 24 bài báo học thuật |
| **Cơ chế chịu lỗi (Fault Tolerance)** | Timeout 15s; tự động chuyển sang đọc snapshot local `data/raw/crossref_response.json` khi mạng gián đoạn hoặc API trả về 429/503 |

### Raw và Clean Schema

| Trường | Kiểu dữ liệu | Bắt buộc | Ý nghĩa nghiệp vụ | Quy tắc xử lý khi thiếu / sai |
| :--- | :--- | :---: | :--- | :--- |
| `paper_id` | `str` | Có | Mã định danh DOI độc nhất | Bỏ qua record nếu thiếu DOI |
| `title` | `str` | Có | Tiêu đề bài báo nghiên cứu | Lọc thẻ HTML/XML, chuẩn hóa khoảng trắng thừa |
| `summary` | `str` | Có | Tóm tắt nội dung khoa học | Lọc bỏ tag `<jats:p>`, loại khoảng trắng thừa; cờ cảnh báo nếu < 30 ký tự |
| `authors` | `list[str]` | Có | Danh sách họ tên tác giả | Ghép `given` + `family`, ghép nối thành `authors_joined` |
| `categories` | `list[str]` | Không | Chuyên ngành phân loại | Nếu rỗng thì gán `["General"]`, lấy chuyên ngành đầu làm `primary_category` |
| `published` | `str` (YYYY-MM-DD) | Có | Ngày xuất bản chính thức | Bóc tách từ `date-parts`, tính toán ra `age_days` |
| `age_days` | `int` | Có | Tuổi đời của bài báo (ngày) | `(run_date - published).days`, dùng để giám sát Freshness SLA |
| `text_for_embedding` | `str` | Có | Ngữ cảnh chuẩn đưa vào vector index | Ghép nối 5 trường theo cấu trúc có tiêu đề rõ ràng |

### Quy tắc tạo `text_for_embedding`
Trường này được cấu trúc hóa chặt chẽ theo 5 phần để mô hình embedding nắm bắt đầy đủ ngữ nghĩa học thuật:
```text
Title: <Tiêu đề bài báo>
Authors: <Danh sách tác giả ngăn cách bởi dấu phẩy>
Published: <Ngày xuất bản YYYY-MM-DD>
Categories: <Chuyên ngành phân loại>
Summary: <Toàn bộ đoạn tóm tắt nghiên cứu đã làm sạch>
```

---

## 6. Evaluation Setup

| Thành phần | Cấu hình thực tế | Ghi chú |
| :--- | :--- | :--- |
| **Số câu hỏi benchmark** | 10 câu | Cố định xuyên suốt 3 pha để đảm bảo tính khách quan |
| **Các dạng câu hỏi (`question_type`)** | `summary` (3 câu), `authors` (3 câu), `date` (2 câu), `categories` (2 câu) | Bao quát đầy đủ các chiều thông tin trong tài liệu |
| **Ground-Truth extraction** | Trích xuất chuẩn xác từ DataFrame gốc | `summary`: câu đầu tóm tắt; `authors`: authors_joined; `date`: published; `categories`: categories_joined |
| **Embedding Model** | Dual-Engine: `Google Gemini Embedding` / `all-MiniLM-L6-v2` | Khởi tạo vector không gian HNSW cosine |
| **Vector Store** | ChromaDB Local Persistent Client | 3 collections độc lập: `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| **Retrieval Top-K** | 4 tài liệu liên quan nhất | Cung cấp đủ ngữ cảnh cho Agent |
| **LLM Provider / Model** | Google Gemini (`gemini-2.5-flash`) | Đánh giá qua cơ chế Structured Output `JudgeVerdict` (Score 1-5, Reasoning) |

> **Tại sao test set phải giữ nguyên cố định xuyên suốt 3 pha?**  
> Trong khoa học dữ liệu và Machine Learning, muốn đo lường chính xác tác động của việc biến đổi dữ liệu (data change/corruption) và đánh giá năng lực phục hồi (repair capability), chúng ta bắt buộc phải áp dụng nguyên tắc **Control Variable (Biến kiểm soát)**. Bằng cách cố định 100% câu hỏi và ground truth, mọi sự sụt giảm hay tăng trưởng của chỉ số (`Hit Rate`, `Token F1`) phản ánh trực tiếp và duy nhất sự thay đổi của chất lượng dữ liệu trong Vector DB, loại trừ hoàn toàn sai số ngẫu nhiên do thay đổi đề bài.

---

## 7. Kết quả Baseline

### Danh mục Artifact bàn giao (Checklist)

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| :--- | :--- | :---: | :--- |
| Raw API Response | `data/raw/crossref_response.json` | Đầy đủ | 24 bài báo nguyên gốc từ Crossref |
| Raw Parsed Records | `data/raw/crossref_records.json` | Đầy đủ | Danh sách `PaperRecord` chuẩn |
| Cleaned Dataset (CSV/JSON) | `data/clean/papers_clean.csv`, `papers_clean.json` | Đầy đủ | 24 dòng sạch, có `text_for_embedding` |
| Vector Index Manifest | `data/embeddings/papers_embeddings.json` | Đầy đủ | Manifest ChromaDB collection `papers-baseline` |
| Benchmark Test Set | `data/eval/test_set.json` | Đầy đủ | 10 câu hỏi chuẩn hóa |
| Baseline Metrics | `data/results/baseline_metrics.json` | Đầy đủ | Hit Rate 100.0%, Token F1 1.0000 |
| Baseline Quality Report | `data/quality/baseline_quality_report.json` | Đầy đủ | GX 1.x validation: PASS (6/6 checks) |
| Freshness SLA Report | `data/quality/freshness_report.json` | Đầy đủ | is_fresh: True (stale_ratio = 4.2%) |
| Baseline Markdown Report | `data/reports/phase1_report.md` | Đầy đủ | Báo cáo chi tiết Pha 1 |

### Baseline Metrics

| Metric | Giá trị thực tế | Diễn giải ý nghĩa |
| :--- | :---: | :--- |
| `retrieval_hit_rate` | **100.0%** (1.0) | 10/10 câu hỏi đều truy xuất chính xác tài liệu mục tiêu trong top 4 kết quả |
| `mean_token_f1` | **1.0000** | Câu trả lời trích xuất trùng khớp hoàn hảo từng token với Ground Truth |
| `judge_accuracy` | **100.0%** (1.0) | LLM Judge đánh giá 10/10 câu trả lời đạt mức chính xác nội dung nghiệp vụ |
| `mean_judge_score` | **5.00 / 5.0** | Điểm số tuyệt đối trên thang điểm 1-5 |

---

## 8. Data Quality & Freshness Observability

### 4 Hàng rào kiểm định Great Expectations 1.x

| Expectation Name | Quality Dimension | Ngưỡng kiểm định | Kết quả Baseline | Trạng thái |
| :--- | :--- | :--- | :---: | :---: |
| `ExpectTableRowCountToBeBetween` | Completeness | [5, 5000] dòng | 24 dòng | **PASS** |
| `ExpectColumnValuesToNotBeNull` | Completeness | Cột `paper_id`, `title`, `text_for_embedding` không được null | 0 dòng null | **PASS** |
| `ExpectColumnValuesToBeUnique` | Uniqueness | Cột `paper_id` là khóa chính duy nhất | 100% unique | **PASS** |
| `ExpectColumnValueLengthsToBeBetween` | Validity | Độ dài trường `summary` tối thiểu 30 ký tự | Min length > 120 chars | **PASS** |

### Freshness SLA Monitoring

| Thuộc tính | Giá trị đo lường thực tế |
| :--- | :--- |
| **Đối tượng đo lường** | Cột `age_days` tính từ ngày chạy đến `published` của 24 bài báo |
| **Bài báo mới nhất / cũ nhất** | Mới nhất: `2026-07-22` / Cũ nhất: `2026-03-28` |
| **Ngưỡng cảnh báo SLA** | Tỷ lệ bài quá hạn (> 180 ngày) không được vượt quá **25.0%** |
| **Kết quả Baseline** | Chỉ có 1 bài > 180 ngày (tỷ lệ **4.2%**) ➡️ **ĐẠT FRESHNESS SLA (`is_fresh = True`)** |

---

## 9. Corruption Scenarios và Idempotent Repair

Tôi đã triển khai đầy đủ 6 kịch bản tiêm độc tố dữ liệu mô phỏng các sự cố phổ biến trong môi trường production:

| STT | Kịch bản Corruption | Cách giả lập trong code | Record bị tác động | Tín hiệu phát hiện (Signal) | Tác động thực tế trên RAG |
| :---: | :--- | :--- | :---: | :--- | :--- |
| **1** | **Drop latest records** | Cắt bỏ 20% bài báo mới nhất | 4 bài mới nhất | GX row count giảm; mất thông tin tươi | Retrieval Hit Rate bị tụt do tài liệu không còn trong DB |
| **2** | **Blank summary** | Xóa rỗng chuỗi tóm tắt thành `""` | 2 bài | GX `ExpectColumnValueLengthsToBeBetween` phát hiện FAIL | Mất ngữ cảnh tóm tắt, trả lời sai câu hỏi summary |
| **3** | **Inject noise** | Chèn chuỗi `### CORRUPTED NOISE %$#@&*! ###` | 2 bài | Làm méo mó vector embedding | Giảm độ tương đồng ngữ nghĩa, tăng hallucination |
| **4** | **Truncate title** | Cắt ngắn tiêu đề thành `"Bad..."` (< 8 ký tự) | 1 bài | Vi phạm entity lookup chính xác | Không thể tìm bài báo theo tiêu đề cụ thể |
| **5** | **Stale date** | Lùi ngày xuất bản về 365 ngày trước cho ~32% bài | 7 bài | Freshness SLA phát hiện vi phạm (> 25%) | Gắn cờ dữ liệu bị mốc meo, vi phạm tính cập nhật |
| **6** | **Duplicate rows** | Nhân đôi các bản ghi đã chọn | 2 bài | GX `ExpectColumnValuesToBeUnique` phát hiện FAIL | Nhân đôi kết quả tìm kiếm, loãng ranking vector |

- **Nhật ký lỗi (Corruption Log):** Được lưu trữ minh bạch tại `data/results/corruption_log.json`.
- **Cơ chế Idempotent Repair:** Thay vì sửa chắp vá trên dữ liệu hỏng, pipeline kích hoạt quy trình tự phục hồi bằng cách quay lại tầng bảo tồn thô `data/raw/crossref_records.json`, chạy lại toàn bộ quy trình làm sạch và nạp lại vào ChromaDB (`papers-repaired`). Nhờ tính bất biến của nguồn gốc (Data Lineage), dữ liệu phục hồi đạt độ sạch 100% và có thể chạy lặp lại vô hạn lần mà kết quả không bị sai lệch (Idempotent).

---

## 10. Bảng đối chiếu định lượng 3 trạng thái

Bảng số liệu thực tế được ghi nhận tự động từ `script/run_corruption_flow.py` và lưu tại `data/reports/corruption_report.md`:

| Chỉ số / Tiêu chí đánh giá | Trạng Thái 1: Baseline (Sạch) | Trạng Thái 2: Corrupted (Tiêm Lỗi) | Trạng Thái 3: Repaired (Phục Hồi) | Thay đổi do lỗi | Mức độ phục hồi |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Data Quality Gate (GX 1.x)** | **PASS (6/6)** | **FAIL (4/6)** | **PASS (6/6)** | Phát hiện 2 vi phạm nghiêm trọng | **100% (Khôi phục)** |
| **Freshness Status** | **Fresh (4.2%)** | **Stale / Fail SLA** | **Fresh (4.2%)** | Vi phạm ngưỡng 25% | **100% (Khôi phục)** |
| **Retrieval Hit Rate** | **100.0%** | **70.0%** | **100.0%** | **Giảm 30.0%** | **Phục hồi 100%** |
| **Mean Token F1** | **1.0000** | **0.7000** | **1.0000** | **Giảm 0.3000** | **Phục hồi 100%** |
| **LLM Judge Accuracy** | **100.0%** | **70.0%** | **100.0%** | **Giảm 30.0%** | **Phục hồi 100%** |
| **Mean Judge Score (1-5)** | **5.00** | **3.90** | **5.00** | **Giảm 1.10 điểm** | **Phục hồi 100%** |

### 2 Kết luận quan hệ nhân quả (Causal Conclusions)
1. **[Dữ liệu bị cắt giảm & bẩn] ➡️ [GX Quality Gate báo động FAIL & Freshness SLA cảnh báo] ➡️ [RAG Hit Rate và Token F1 tụt dốc 30%]:**  
   Đây là minh chứng rõ rệt cho hiện tượng **Lỗi thầm lặng (Silent Failure)**. Không có dòng lệnh nào bị crash, nhưng câu trả lời của AI đã bị sai lệch nghiêm trọng do vector database bị nhiễm độc. Nếu không có trạm kiểm soát Data Observability ở giữa, lỗi này sẽ lọt thẳng lên người dùng cuối trong thực tế.
2. **[Idempotent Repair từ Raw Preservation] ➡️ [GX Gate chuyển sang PASS] ➡️ [RAG Metrics phục hồi hoàn toàn 100% phong độ]:**  
   Chứng minh rằng kiến trúc lưu trữ nguyên vẹn dữ liệu gốc (Raw Preservation) là nền tảng tối quan trọng cho năng lực tự chữa lành (Self-Healing) của mọi hệ thống AI hiện đại.

---

## 11. Vấn đề tích hợp quan trọng và cách xử lý

1. **Vấn đề 1: Lỗi `FileNotFoundError: papers_clean.json` khi chạy smoke test Bước 4:**
   - *Triệu chứng:* Ở Bước 3, câu lệnh kiểm tra ban đầu chỉ biến đổi DataFrame trên RAM và in `len(df)` mà chưa lưu file xuống đĩa, dẫn đến Bước 4 gọi `pd.read_json(s.paths.clean_json)` bị văng lỗi không tìm thấy file.
   - *Cách xử lý:* Tôi đã cập nhật hàm làm sạch và lệnh Bước 3 để tự động xuất dữ liệu ra cả 2 định dạng `papers_clean.csv` và `papers_clean.json`, đồng thời sửa lại tài liệu `Guide.md` để đảm bảo tính nhất quán.
2. **Vấn đề 2: Tối ưu hóa mô hình Embedding không phụ thuộc gói nặng PyTorch:**
   - *Triệu chứng:* Thư viện `sentence-transformers` yêu cầu kéo theo PyTorch (~2GB), tốn nhiều tài nguyên và thời gian tải.
   - *Cách xử lý:* Tôi đã thiết kế lớp `MiniLMEmbeddings` theo cơ chế **Dual-Engine / Auto-Fallback**: Nếu chưa có `sentence-transformers`, hệ thống tự động gọi Google Gemini Embeddings (`models/gemini-embedding-001` / `models/text-embedding-004`) thông qua `GOOGLE_API_KEY` có sẵn; khi môi trường cài đặt `sentence-transformers`, hệ thống tự động dùng lại `all-MiniLM-L6-v2` đúng theo tiêu chuẩn của Rubric.

---

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| :--- | :--- | :--- |
| **Quy mô tập dữ liệu** | 24 tài liệu là mẫu đại diện phù hợp cho bài lab phòng thí nghiệm nhưng chưa phản ánh tải lớn | Mở rộng scale pipeline lên 5.000 - 10.000 bài báo và sử dụng cơ chế batch processing / streaming ingestion |
| **Cơ chế Repair thủ công** | Hiện tại quy trình repair được gọi thông qua script điều phối `run_corruption_flow.py` | Tích hợp webhook tự động: Khi GX Gate trả về `success=False`, hệ thống tự động kích hoạt worker rollback và repair ngay lập tức (Automated Self-Healing - Bonus B2) |
| **Giao diện Observability** | Báo cáo hiện tại xuất dưới dạng Markdown và JSON log | Xây dựng Web Dashboard thời gian thực (Streamlit / Gradio) hiển thị biểu đồ phân bố độ tuổi tài liệu và trạng thái kiểm định (Bonus B1) |

---

## 13. Checklist nghiệm thu bài nộp

- [x] Thông tin cá nhân, vai trò Solo và repository chính xác.
- [x] Đã hoàn thành 100% các file mã nguồn: không còn bất kỳ hàm `TODO` hay `NotImplementedError` nào.
- [x] Lệnh tái hiện `run_phase1.py` và `run_corruption_flow.py` chạy trơn tru end-to-end, exit code 0.
- [x] Cả 3 trạng thái (Baseline, Corrupted, Repaired) dùng chung 100% bộ đề thi `test_set.json`.
- [x] Bảng số liệu đối chiếu khớp hoàn toàn với các file JSON trong `data/results/` và `data/quality/`.
- [x] File `.gitignore` đã được cấu hình chuẩn, không ignore các file deliverables `.json` và không chứa secret / `.env`.
- [x] Hoàn thiện đầy đủ `group_report.md` và `individual_report.md`.
