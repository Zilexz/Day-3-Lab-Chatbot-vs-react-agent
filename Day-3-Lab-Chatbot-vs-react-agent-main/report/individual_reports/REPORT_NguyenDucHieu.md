# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Nguyễn Đức Hiếu
- **Student ID**: 2A202600680
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

*Mô tả đóng góp cụ thể vào codebase.*

- **Modules Implemented**:
  - `src/agent/agent.py` — Triển khai đầy đủ vòng lặp ReAct: Thought → Action → Observation, parse regex 2 dạng (có ngoặc và không ngoặc), retry khi parse fail, fallback khi hết max_steps.
  - `src/tools/calculator.py` — Tính toán toán học an toàn bằng `eval` giới hạn scope, hỗ trợ sqrt, log, trig.
  - `src/tools/tax_calculator.py` — Tính VAT theo 12 mã quốc gia ISO, có validation rõ ràng.
  - `src/tools/search.py` — Mock web search với knowledge base nội bộ.
  - `src/tools/weather.py` — Thông tin thời tiết mock theo tên thành phố.
  - `src/chatbot/chatbot.py` — Baseline chatbot đơn giản, 1 lần gọi LLM.
  - `src/telemetry/metrics.py` — Bảng giá thực tế (GPT-4o, Gemini, Claude), tổng hợp P50/P99 latency.
  - `main.py` — CLI với 3 chế độ: `chatbot`, `agent`, `compare`; 5 test cases mẫu.

- **Code Highlights**:

  Vòng lặp ReAct trong `src/agent/agent.py` — cơ chế scratchpad tích lũy:
  ```python
  while steps < self.max_steps:
      result = self.llm.generate(scratchpad, system_prompt=self.get_system_prompt())
      content = result.get("content", "").strip()

      # Kiểm tra Final Answer trước
      final_answer = self._parse_final_answer(content)
      if final_answer:
          return final_answer

      # Parse và thực thi tool
      thought, tool_name, tool_args = self._parse_action(content)
      observation = self._execute_tool(tool_name, tool_args)
      scratchpad += f"Thought: {thought}\nAction: {tool_name}({tool_args})\nObservation: {observation}\n"
  ```

- **Documentation**: Agent dùng scratchpad tích lũy thay vì memory riêng — toàn bộ context (Question + Thought/Action/Observation) được truyền vào LLM mỗi bước, giúp LLM "nhớ" những gì đã làm mà không cần state bên ngoài. Parse `Final Answer` trước `Action` để tránh xung đột khi LLM vừa có action vừa có final answer trong cùng 1 response.

---

## II. Debugging Case Study (10 Points)

*Phân tích một failure cụ thể bằng logging system.*

- **Problem Description**: Trong quá trình phát triển, agent gọi `calculate_vat(500, Germany)` — cả tên tool lẫn argument đều sai. Tên đúng phải là `calc_tax`, argument phải là ISO code `DE` chứ không phải tên đầy đủ `Germany`.

- **Log Source** (trích từ `logs/2026-06-01.log`):
  ```json
  {"event": "HALLUCINATION", "data": {
    "tool_name": "calculate_vat",
    "known_tools": ["calculator", "search", "calc_tax", "get_weather"]
  }}
  {"event": "TOOL_CALL", "data": {
    "tool": "calc_tax", "args": "Germany",
    "observation": "Error: Unknown country code 'GERMANY'. Supported: VN, US, DE, ..."
  }}
  ```

- **Diagnosis**: System prompt v1 chỉ liệt kê tên tool mà không có ví dụ cụ thể. LLM tự suy ra tên tool theo hiểu biết của mình — hallucinate thành `calculate_vat`. Tương tự, không có hướng dẫn rõ về format argument nên LLM dùng tên đầy đủ (`Germany`) thay vì ISO code (`DE`).

- **Solution**: Cập nhật description của `calc_tax` — thêm `"Example: calc_tax(500, VN)"` và ghi rõ `"country_code must be ISO 2-letter code"`. Sau khi fix, agent gọi đúng `calc_tax(500, DE)` ngay từ bước đầu.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Nhận xét về khả năng suy luận.*

1. **Reasoning**: Block `Thought:` là điểm khác biệt cốt lõi. Chatbot trả lời ngay bằng "bản năng" — nếu câu trả lời vượt quá training data (dữ liệu real-time, tính toán chính xác với số cụ thể), nó sẽ bịa hoặc từ chối. ReAct agent buộc LLM viết ra kế hoạch trước khi hành động — khi đã commit với một Thought cụ thể, LLM ít có xu hướng hallucinate hơn vì nó tự ràng buộc mình vào một hướng đi có logic.

2. **Reliability**: Agent thực sự **kém hơn** chatbot trong một số trường hợp:
   - Câu hỏi đơn giản ("Thủ đô Việt Nam là gì?"): Agent mất ~2 giây và tốn gần 7x token so với chatbot trả lời ngay trong 0.7 giây.
   - Khi tool trả về dữ liệu sai (mock data): Agent tin tuyệt đối vào Observation — nếu tool sai thì answer cũng sai, trong khi chatbot dùng knowledge thật từ training.

3. **Observation**: Mỗi Observation tốt giúp agent thu hẹp không gian không chắc chắn. Khi Observation có cấu trúc rõ ràng (`"Tax=100,000 VND, Total=1,100,000 VND"`), LLM đưa ra Final Answer ngay ở bước tiếp theo. Khi Observation là lỗi hoặc mơ hồ, LLM có xu hướng retry thay vì đổi chiến lược — đây là điểm cần cải thiện bằng cơ chế "reflection" trong các hệ thống phức tạp hơn.

---

## IV. Future Improvements (5 Points)

*Đề xuất mở rộng lên hệ thống production.*

- **Scalability**: Thay thế vòng lặp đồng bộ hiện tại bằng async tool execution — nhiều tool có thể chạy song song nếu independent. Với 10+ tools, dùng vector embedding để retrieve tool liên quan thay vì liệt kê tất cả trong system prompt, giảm prompt tokens 60–70%.

- **Safety**: Thêm một Supervisor LLM nhỏ (GPT-4o-mini) kiểm tra mỗi Action trước khi thực thi: "Hành động này có phù hợp với intent người dùng không? Có rủi ro gì không?" — đây là pattern Constitutional AI at inference time.

- **Performance**: Chuyển sang LangGraph state machine để quản lý branching phức tạp hơn (parallel tool calls, conditional routing, error recovery), thay cho vòng lặp while thủ công hiện tại.

---

> [!NOTE]
> Submit this report by renaming it to `REPORT_[YOUR_NAME].md` and placing it in this folder.
