# RAG-SVV

Repo có ba hướng riêng biệt: Switch (Unity mod tooling), web research, và game mới `midgard-offline/`.

## Midgard offline

### Ưu tiên hiện tại: client gốc và sprite Ragnarok

- Người dùng đã xác nhận muốn client gốc đầy đủ, giữ sprite Ragnarok và thêm AI, KHÔNG dùng prototype vẽ pixel riêng làm bản bàn giao. Cửa sổ prototype từng gây nhầm lẫn; không lặp lại khi preview hoặc báo kết quả.
- Project đã khôi phục: `midgard-offline/work/recovered/`; bản đã vá offline: `midgard-offline/work/recovered-offline/`. Các thư mục này bị Git bỏ qua. Mã/tài nguyên gốc không được đưa lên repo công khai.
- Godot đúng phiên bản 4.7.2; GDRE 2.7.4. Các công cụ sẵn trong `work/tools/`. Full sprites/maps được giữ trong project Godot, không thay bằng hình tự vẽ của `engine.js`/`game.js`.
- Helper tự viết: `tools/prepare-original-offline.py`, `tools/localize_original.py`, `tools/install-original-assistant.py`, các helper export original. Khi sửa source riêng, cập nhật helper để có thể tái lập.
- `original-addons/offline_assistant.gd` là overlay tự viết; NPC theo luật phải ghi rõ chưa phải LLM. LLM Qwen cục bộ đã thử CPU nhưng chất lượng chưa đạt, không bật mặc định hoặc ghi hoàn thiện native Android.
- Save offline riêng; test phải dùng `--offline-test` và các tệp test riêng, không dùng `--coop` gốc vì nó có thể reset profile thử nghiệm. Tổ đội bot phải được lưu và khôi phục cả trạng thái.
- Nâng nền 0.2.5: giữ pin ZIP 0.2.0, áp `config/official-update.json` qua `tools/update-original-client.py` TRƯỚC lớp offline/addon. Giữ các thay đổi Cloud Wave 28; xem `docs/UPSTREAM_0_2_5_UPGRADE.md`. Nhập save phải chờ IndexedDB và thay cả rescue localStorage của upstream; xem `docs/SAVE_PORTABILITY.md`.
- Xem `docs/ORIGINAL_CLIENT.md` và `docs/FEATURE_PARITY.md` trước khi tiếp tục. Xác nhận artifact gốc và QA thật; số bản ghi dữ liệu hoặc việc build prototype không chứng minh full tính năng.
- Người dùng ưu tiên tiếp tục bằng ChatGPT web + GitHub, không phụ thuộc Codex desktop. Đọc `midgard-offline/docs/WEB_GITHUB_DEVELOPMENT.md`; workflow `original-client.yml` tự tải client chính thức, kiểm hash, recover và build trong runner. Không bảo người dùng quay về máy này khi chỉ cần sửa bản dịch/addon hoặc build.

### Prototype HTML/JS cũ (hướng phụ)

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
