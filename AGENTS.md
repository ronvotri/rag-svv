# RAG-SVV

Repo có ba hướng riêng biệt: Switch (Unity mod tooling), web research, và game mới `midgard-offline/`.

## Midgard offline

- Game độc lập tiếng Việt, chơi đơn, chạy trực tiếp bằng `index.html` khi ngắt mạng. Không phụ thuộc client PC, API, tài khoản hoặc server gameplay.
- Giữ runtime buildless: HTML/CSS/JS thường, Canvas tự vẽ. Không thêm CDN, font online hoặc bước tải dependency để chơi.
- `engine.js`: luật chơi thuần JS, dùng được trong Node tests. `game.js`: giao diện, điều khiển, âm thanh và hình vẽ. `style.css`: giao diện responsive.
- Node.js >=20. Từ repo root chạy `node --test midgard-offline/tests/*.test.cjs` và `node midgard-offline/tools/build.mjs`. Không cần npm install.
- ZIP: `midgard-offline/dist/midgard-offline-0.1.0.zip`. Đầu ra được Git bỏ qua. CI `.github/workflows/midgard-offline.yml` cung cấp artifact sau mỗi push/PR thay đổi game.
- Preview tùy chọn: `node midgard-offline/tools/serve.mjs`, URL http://127.0.0.1:8765/. Mở trực tiếp file vẫn phải hoạt động.
- Save có schema version và kiểm tra dữ liệu; thay schema cần migration. Lưu browser + xuất/nhập JSON; không hứa tự đồng bộ thiết bị.
- Không đưa EXE, PCK, bản dump, secret hoặc tài sản game bên thứ ba vào Git. `work/`, `private/`, `imported/` là dữ liệu cục bộ ignored; bản build không đọc chúng.
- Đây là prototype độc lập, chưa phải bản clone hoặc chuyển đổi đầy đủ của Midgard Survivors. Phân biệt phần đã test với phần chỉ dự kiến.
- Có thể làm việc song song bằng agent nếu người dùng yêu cầu; chia quyền sửa file rõ ràng.
