# Báo Cáo Pha 1: Baseline Data Pipeline & Observability

**Ngày báo cáo:** 2026-09-25  
**Nguồn dữ liệu:** Crossref REST API  

---

## 1. Tổng Quan Thu Thập & Làm Sạch Dữ Liệu (Ingestion & Lineage)
- **Số bản ghi thô thu thập (Raw Records):** 24
- **Số bản ghi sạch sau xử lý (Clean Records):** 24
- **Bảo lưu nguồn gốc (Raw Preservation):** Đã lưu trữ thành công `crossref_response.json` và `crossref_records.json`.
- **Cấu trúc trường `text_for_embedding`:** Đầy đủ 5 thành phần (Title, Authors, Published, Categories, Summary).

---

## 2. Kiểm Soát Chất Lượng Dữ Liệu (Data Observability Gate với Great Expectations 1.x)
- **Trạng thái kiểm định GX:** **ĐẠT (PASS)** (6/6 expectations vượt qua)
- **Hàng rào kiểm định áp dụng:**
  1. `ExpectTableRowCountToBeBetween`: Số dòng trong khoảng [5, 5000].
  2. `ExpectColumnValuesToNotBeNull`: `paper_id`, `title`, `text_for_embedding` không bị rỗng.
  3. `ExpectColumnValuesToBeUnique`: `paper_id` là khóa chính duy nhất.
  4. `ExpectColumnValueLengthsToBeBetween`: Trường `summary` có độ dài tối thiểu 30 ký tự.

---

## 3. Giám Sát Độ Tươi Mới (Freshness Monitoring & SLA)
- **Trạng thái độ tươi:** **ĐẠT SLA (Fresh)**
- **Bài báo mới nhất:** 2026-07-22
- **Bài báo cũ nhất:** 2026-03-28
- **Số dòng quá hạn (> 180 ngày):** 1/24
- **Tỉ lệ quá hạn:** 4.17% (Ngưỡng cảnh báo SLA: > 25.00%)

---

## 4. Đo Lường Hiệu Năng RAG Cơ Sở (Baseline Benchmarks)
- **Số lượng câu hỏi đánh giá:** 10
- **Retrieval Hit Rate:** **100.00%**
- **Mean Token F1:** **1.0000**
- **LLM Judge Accuracy:** **100.00%**
- **Mean Judge Score (Thang 1-5):** **5.00 / 5.0**

---

## 5. Kết Luận Pha 1
Dữ liệu sạch đã vượt qua toàn bộ các cổng kiểm định chất lượng dữ liệu và đạt tiêu chuẩn Freshness SLA. Chỉ số Retrieval và QA Agent ở mức chuẩn xác cao, thiết lập mốc so sánh (Baseline) vững chắc cho các thử nghiệm tiếp theo.
