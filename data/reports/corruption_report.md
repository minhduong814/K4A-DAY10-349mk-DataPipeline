# Báo Cáo Đối Chiếu 3 Trạng Thái: Baseline vs Corrupted vs Repaired

**Bài lab:** Day 10 - Data Pipeline & Data Observability  
**Mục tiêu:** Đo lường sự suy giảm hiệu năng RAG khi gặp dữ liệu bẩn (Data Corruption) và chứng minh năng lực tự phục hồi (Self-Healing).

---

## 1. Bảng Đối Chiếu Chỉ Số Định Lượng (3 Trạng Thái)

| Chỉ số / Tiêu chí đánh giá | Trạng Thái 1: Baseline (Sạch) | Trạng Thái 2: Corrupted (Tiêm Lỗi) | Trạng Thái 3: Repaired (Sau Phục Hồi) |
| :--- | :---: | :---: | :---: |
| **Data Quality Gate (GX 1.x)** | **PASS** | **FAIL** | **PASS** |
| **Freshness SLA (Tỷ lệ quá hạn)** | Fresh (< 25%) | **Fresh (13.6%)** | **Fresh (4.2%)** |
| **Retrieval Hit Rate** | **100.0%** | **70.0%** | **100.0%** |
| **Mean Token F1** | **1.0000** | **0.7000** | **1.0000** |
| **LLM Judge Accuracy** | **100.0%** | **70.0%** | **100.0%** |
| **Mean Judge Score (1-5)** | **5.00** | **3.90** | **5.00** |

---

## 2. Phân Tích Hiện Tượng "Lỗi Thầm Lặng" (Silent Failure)
Khi 6 kịch bản dữ liệu bẩn được tiêm vào:
1. **Mất bài báo mới nhất:** Hit Rate sụt giảm do vector database không còn chứa đúng tài liệu mục tiêu.
2. **Xóa trắng tóm tắt & chèn nhiễu ký tự:** Embedding bị méo mó, làm mất thông tin ngữ nghĩa quan trọng.
3. **Cắt ngắn tiêu đề & trùng lặp bản ghi:** Vi phạm tính duy nhất của khóa chính và làm sai lệch quá trình tra cứu thực thể.
4. **Hậu quả trên Agent:** Code chạy không hề phát sinh exception runtime (Silent Failure), nhưng chỉ số trả lời của AI giảm sút nghiêm trọng. Data Observability Gate (GX 1.x) đã phát hiện và chặn đứng trạng thái dữ liệu này.

---

## 3. Cơ Chế Phục Hồi Đảm Bảo Tính Bất Biến (Idempotent Repair)
- Nhờ lưu trữ nguyên vẹn dữ liệu gốc ban đầu (`crossref_records.json` / `crossref_response.json`), hệ thống kích hoạt luồng tái tạo pipeline từ tầng raw.
- Kết quả sau phục hồi cho thấy các chỉ số quay trở về đúng mức ban đầu:
  - Retrieval Hit Rate: **100.0%** (khôi phục hoàn toàn).
  - Data Quality: Đạt 100% tiêu chí kiểm định Great Expectations.
  - Freshness SLA: Trở lại ngưỡng an toàn dưới 25%.

---

## 4. Kết Luận
Thử nghiệm đã chứng minh tầm quan trọng sống còn của việc triển khai Data Observability Gate trước khi nạp dữ liệu vào Vector Database, đồng thời khẳng định giá trị của cơ chế Raw Preservation trong việc tự chữa lành (Self-Healing) hệ thống.
