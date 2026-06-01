# Group Report: Lab 3 - Production-Grade Agentic System

- **Team Name**: Team 01
- **Team Members**: Nguyễn Văn A, Trần Thị B, Lê Văn C
- **Deployment Date**: 2026-06-01

---

## 1. Executive Summary

*Tổng quan về mục tiêu agent và tỷ lệ thành công so với chatbot baseline.*

- **Success Rate**: Agent đạt **5/5 (100%)** trên 5 test cases; Chatbot chỉ đạt **2/5 (40%)**.
- **Key Outcome**: Agent giải quyết đúng 100% bài toán tính toán, thuế, thời tiết và đa bước nhờ sử dụng tools thực tế. Chatbot chỉ trả lời đúng những câu hỏi đơn giản nằm trong training data (Q1, Q5), còn lại hoặc từ chối hoặc trả lời chung chung không có số liệu cụ thể.

---

## 2. System Architecture & Tooling

### 2.1 ReAct Loop Implementation

*Mô tả vòng lặp Thought-Action-Observation.*

```
User Input
    │
    ▼
┌─────────────────────────────────────┐
│          ReAct Agent Loop           │
│                                     │
│  Question: <user_input>             │
│  Thought:  <lập luận bước tiếp>     │
│  Action:   <tool_name>(<args>)      │
│  Observation: <kết quả thực từ tool>│
│  ... (lặp tối đa max_steps=6)       │
│  Final Answer: <câu trả lời cuối>   │
└─────────────────────────────────────┘
    │
    ▼
  Output
```

Cơ chế: LLM nhận toàn bộ scratchpad tích lũy (Question + các Thought/Action/Observation trước) cùng system prompt mô tả tools. Mỗi bước LLM viết ra Thought (lý do) rồi Action (tool cần gọi). Agent parse action, thực thi tool thực, đưa Observation trở lại cho LLM. Vòng lặp dừng khi LLM xuất `Final Answer:` hoặc đạt `max_steps`.

### 2.2 Tool Definitions (Inventory)

| Tool Name | Input Format | Use Case |
| :--- | :--- | :--- |
| `calculator` | Biểu thức toán học Python | Tính toán chính xác, tránh hallucination số học |
| `search` | Câu truy vấn tự do | Tìm kiếm thông tin theo chủ đề |
| `calc_tax` | `amount, country_code` (ISO 2 chữ cái) | Tính VAT theo từng quốc gia |
| `get_weather` | Tên thành phố tiếng Anh | Lấy thông tin thời tiết hiện tại |

**Tiến hóa thiết kế tool (v1 → v2):**
- **v1**: Tool chỉ nhận 1 argument, không có validation, mô tả chung chung.
- **v2**: Thêm error handling rõ ràng, hỗ trợ multi-argument, thêm ví dụ cụ thể trong description để LLM gọi đúng format.

### 2.3 LLM Providers Used

- **Primary**: GPT-4o (OpenAI) — độ chính xác cao nhất cho reasoning và tool calling
- **Secondary (Backup)**: Gemini 1.5 Flash (Google) — chi phí thấp hơn ~30x, phù hợp prototype

---

## 3. Telemetry & Performance Dashboard

*Số liệu thực từ 5 test cases chạy với GPT-4o — lấy trực tiếp từ `logs/2026-06-01.log` và `logs/2026-06-01_summary.txt`.*

| Metric | Chatbot | Agent |
| :--- | :---: | :---: |
| Tỷ lệ trả lời đúng | **2/5 (40%)** | **5/5 (100%)** |
| Tổng tokens dùng | **654** | **4,476** |
| Agent tốn hơn (tokens) | — | **6.8x** |
| Tổng chi phí (USD) | **$0.004775** | **$0.013415** |
| Avg latency / câu hỏi | **1,705 ms** | **1,623 ms** |
| Avg latency / bước | — | **711 ms/bước** |
| Avg số bước / câu hỏi | — | **2.0 bước** |

**Chi tiết từng câu hỏi:**

| # | Câu hỏi | Chatbot tokens | Agent tokens | Chatbot đúng? | Agent đúng? |
| :- | :--- | :---: | :---: | :---: | :---: |
| Q1 | Tính 123 × 456 | 60 | 828 | ✓ (may mắn) | ✓ (dùng tool) |
| Q2 | Thuế 1M VND tại VN | 306 | 960 | ✗ (chung chung) | ✓ |
| Q3 | Thời tiết Hà Nội | 80 | 854 | ✗ (từ chối) | ✓ |
| Q4 | Search ReAct + tính 2^10 | 154 | 1,436 | ✗ (bịa search) | ✓ |
| Q5 | Thủ đô Việt Nam | 54 | 398 | ✓ | ✓ |

- **Average Latency (P50)**: Chatbot 1,718 ms | Agent 1,432 ms/câu hỏi
- **Max Latency (P99)**: Chatbot 2,917 ms (Q2) | Agent 2,361 ms (Q2)
- **Average Tokens per Task**: 131 tokens (chatbot) vs 895 tokens (agent)
- **Total Cost of Test Suite**: $0.004775 (chatbot) + $0.013415 (agent) = **$0.018190**

**Nhận xét:**
- Agent tốn gấp **6.8x token** và **2.8x chi phí** so với chatbot, nhưng độ chính xác gấp **2.5x**.
- Với bài toán cần dữ liệu thực hoặc tính toán, agent là lựa chọn bắt buộc.
- Với câu hỏi đơn giản (Q5), chatbot nhanh hơn và rẻ hơn — agent thậm chí mất thêm 1 bước không cần thiết.

---

## 4. Root Cause Analysis (RCA) - Failure Traces

*Phân tích sâu các trường hợp agent/chatbot thất bại.*

### Case Study 1: Chatbot Hallucination — Câu hỏi tính thuế

- **Input**: "How much tax would I pay on 1,000,000 VND in Vietnam?"
- **Chatbot Observation**: Trả lời chung chung về nhiều loại thuế (thu nhập, VAT, doanh nghiệp...) mà không tính ra con số cụ thể nào.
- **Root Cause**: Chatbot không có công cụ tính toán, phụ thuộc hoàn toàn vào training data — nên không thể đưa ra kết quả chính xác với số liệu cụ thể.
- **Agent Result**: Gọi `calc_tax(1000000, VN)` → trả về đúng `Tax=100,000 VND, Total=1,100,000 VND`.

### Case Study 2: Agent Over-Engineering — Câu hỏi đơn giản bị xử lý phức tạp

- **Input**: "What is the capital of Vietnam?" (chạy lần 2)
- **Chatbot**: Trả lời ngay "The capital of Vietnam is Hanoi." — 54 tokens, 654ms.
- **Agent Observation từ log**: Agent gọi `search(capital of Vietnam)` → nhận về thông tin GDP của Việt Nam (không liên quan). Gọi lại `search(what is the capital city of Vietnam)` → vẫn không có. Bước 3 mới dùng knowledge của chính mình để trả lời đúng. Tốn 1,433 tokens và 2,337ms.
- **Root Cause**: Agent không biết khi nào nên dùng knowledge sẵn có thay vì gọi tool. Search tool mock chỉ trả về thông tin GDP, không có thông tin về thủ đô.
- **Lesson**: Agent không phải lúc nào cũng tốt hơn chatbot — với câu hỏi general knowledge, chatbot nhanh hơn và rẻ hơn gấp nhiều lần.

### Case Study 3: Hallucinated Tool Name (phát hiện trong quá trình dev)

- **Input**: "How much is the tax for 500 in Germany?"
- **Observation**: Agent v1 gọi `calculate_vat(500, Germany)` — cả tên tool lẫn argument đều sai.
- **Root Cause**: System prompt không có ví dụ cụ thể, LLM tự suy ra tên tool và argument không đúng format ISO code.
- **Fix (v2)**: Thêm `"Example: calc_tax(500, VN)"` và `"2-letter ISO country code"` vào description của tool.

---

## 5. Ablation Studies & Experiments

### Experiment 1: Prompt v1 vs Prompt v2

- **Diff**: Thêm ví dụ cụ thể (`Example: calc_tax(500, VN)`) vào mô tả từng tool trong system prompt.
- **Result**: Giảm lỗi gọi sai tool/argument; agent gọi đúng format ngay từ bước đầu thay vì phải retry.

### Experiment 2 (Bonus): Chatbot vs Agent

| Case | Chatbot Result | Agent Result | Winner |
| :--- | :--- | :--- | :--- |
| Tính 123 × 456 | 56,088 ✓ (may mắn) | 56,088 ✓ (dùng calculator) | **Agent** (đáng tin hơn) |
| Thuế 1M VND tại VN | Trả lời chung chung, không có số | 100,000 VND VAT ✓ | **Agent** |
| Thời tiết Hà Nội | "Tôi không có real-time data" | 32°C, Nắng nóng ✓ | **Agent** |
| Multi-tool: search + tính 2^10 | Tự bịa search result | Search + tính đúng 1024 | **Agent** |
| Thủ đô Việt Nam | Hà Nội ✓ | Hà Nội ✓ | **Draw** |

---

## 6. Production Readiness Review

*Đánh giá khả năng triển khai thực tế.*

- **Security**: Tool args hiện chưa được sanitize đầy đủ — cần thêm whitelist input, giới hạn scope của `eval()` trong calculator.
- **Guardrails**: Đã có `max_steps=6` để tránh infinite loop và chi phí không kiểm soát. Cần thêm budget cap theo USD.
- **Scaling**: Tools hiện được hardcode — cần chuyển sang tool registry động để thêm/bỏ tool mà không sửa code agent.

---

> [!NOTE]
> Submit this report by renaming it to `GROUP_REPORT_[TEAM_NAME].md` and placing it in this folder.
