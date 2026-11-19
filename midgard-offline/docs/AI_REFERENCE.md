# AI ngoại tuyến và tham khảo PKM Chuyển Sinh

Đã đọc hướng dẫn repo PKMSVV và các tài liệu `docs/CLOUD_HANDOFF.md`, `docs/LAN_AI_1_5_18.md`, cùng cấu trúc `src/lan/lan-ai.js` và `src/lan/solo-ai-bus.js` trên máy người dùng. Không sửa PKMSVV, không đọc hoặc sao chép khóa ký Android, thông tin đăng nhập hay cấu hình bí mật.

PKMSVV có AI gameplay dựa trên luật: bot là nhân vật thật của engine, dùng máu, kỹ năng, hồi chiêu và lựa chọn thưởng hợp lệ. AI có thể né nguy hiểm, giữ khoảng cách, cứu đồng đội và hoạt động qua bộ điều phối trong bộ nhớ khi chơi ngoại tuyến. Chưa tìm thấy mô hình ngôn ngữ/chatbot trong các thư mục mã nguồn/tài liệu đã khảo sát; từ “AI” ở đây không tự chứng minh có chat sinh văn bản.

`ai.js` của Midgard được viết mới theo các nguyên tắc đó, không sao chép mã game PKMSVV. Module chỉ trả về quyết định; engine chịu trách nhiệm áp dụng chuyển động, sát thương, hồi máu, hồi sinh, tài nguyên và hồi chiêu theo luật trận. Không có “sát thương giả” chỉ vì bot đứng gần quái.

## Hợp đồng tích hợp

- Global browser: `MidgardAI`. Node: `require('../ai.js')`.
- `COMPANIONS`: ba vai trò `guardian`, `ranger`, `healer`, kèm nghề gợi ý và phạm vi.
- `decideCompanion(actor, snapshot)` không sửa đầu vào. Actor cần `id`, `x`, `y`, `hp`, `maxHp`, `role`, `range`, `speed`; tùy chọn `healCooldown`, `dashCooldown`, `slot`, `r`.
- Snapshot gồm `player`, `allies`, `enemies`, `hazards`, `obstacles`. Đối tượng có vị trí `x/y`; quái có `hp/r/type/id`; vùng nguy hiểm có `r/life/active`; vật cản có `r`; người bị hạ có thể đặt `revivable:false` để cấm cứu.
- Kết quả `{move:{x,y}, targetId, healId, reviveId, dash, reason}` chỉ là ý định. Engine phải kiểm lại sống/chết, khoảng cách, đường đi, hồi chiêu và điều kiện cho phép trước khi thực thi. Không chấp nhận quyết định như một lệnh có quyền vượt luật.
- `chooseUpgrade(actor, legalChoices)` chỉ chọn một đối tượng thật trong danh sách hợp lệ mà engine đưa ra.
- `chat(text, context)` trả về `{intent,text,suggestions,mode:'offline-rules'}`. Context tùy chọn gồm `run`, `player`, `save`. Câu trả lời có nhận biết máu, vàng và boss từ context nhưng không sửa dữ liệu.

## Chat và giới hạn

Hướng dẫn viên tiếng Việt hoạt động bằng nhận diện chủ đề và kiến thức viết sẵn: điều khiển, nghề, build nâng cấp, sinh tồn, thủ lĩnh, AI, lưu/chuyển máy và rèn luyện. Đây là chat theo luật ngoại tuyến, **không phải LLM**. Khi không hiểu, nó nói rõ giới hạn, không giả vờ đã gọi dịch vụ hay đã làm thay đổi dữ liệu game.

Không có API key, request mạng, mô hình tải từ Internet hoặc phụ thuộc ngoài trong module. Nếu sau này muốn chat sinh văn bản tự do khi không mạng, cần chọn và đóng gói một mô hình chạy cục bộ, xác định dung lượng, RAM và khả năng hỗ trợ Android/PC. Chưa triển khai hoặc kiểm thử mô hình đó ở bản này.

Các quyết định né tránh và cứu người là heuristic có giới hạn; không bảo đảm bot sống sót khi bị vây. Unit test không thay thế kiểm thử gameplay và hiệu năng trên thiết bị thực.
