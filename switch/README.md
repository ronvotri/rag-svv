# Ragnarok Survivors — bản Việt hóa Nintendo Switch

**Nguồn tham khảo:** https://github.com/type0labs-dev/ragnarok-survivors

Đây là bản mod **Vampire Survivors** trên Nintendo Switch, không phải trò chơi trực tuyến tại ro-survivors.com.

## Tình trạng
- Đã có công cụ thử nghiệm áp dụng chuỗi tiếng Việt vào I2Languages.
- **Chưa** có bản build hoàn chỉnh hoặc kiểm thử trong game.
- Cần font có đủ dấu tiếng Việt và bản dump trò chơi hợp pháp.
- Không đưa NSP/ROMFS/tài nguyên của game hay khóa hệ thống lên GitHub.

## File hiện hành
- Bản dịch thử nghiệm: [`../locales/vi-VN.json`](../locales/vi-VN.json)
- Công cụ áp dụng: [`../tools/apply_vi.py`](../tools/apply_vi.py)
- Hướng dẫn build: [README chính](../README.md)

Các file ở thư mục gốc được **giữ nguyên** để không làm hỏng lệnh build hiện tại. Khi chuyển cấu trúc, cần cập nhật đường dẫn công cụ cùng lúc.

## Phân biệt
Không sử dụng mã/asset Switch để dựng server game web. Phần Switch và web có kiến trúc và quyền sở hữu khác nhau.
