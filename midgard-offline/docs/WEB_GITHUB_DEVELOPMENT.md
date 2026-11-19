# Tiếp tục bằng ChatGPT web và GitHub

Mục tiêu: phát triển client gốc với sprite Ragnarok từ bất kỳ máy nào, không cần ứng dụng Codex desktop, ổ E: hoặc máy Windows ban đầu. GitHub lưu các thay đổi tự viết; GitHub Actions tải bản nền chính thức, khôi phục, vá, kiểm tra và build trên máy runner.

**Đã xác minh một lượt Windows thành công:** [run 43785523181](https://github.com/ronvotri/rag-svv/actions/runs/43785523181), commit `f4262bb`. Xem [kết quả và artifact](CLOUD_BUILD_VERIFIED.md). Tiếp tục ở nhánh `feature/original-offline`; thay đổi mã/bản dịch liên quan sẽ tự kích hoạt build Windows trên nhánh này.

## Repo công khai vẫn build được game gốc

Repo không phải chứa lại toàn bộ client hoặc sprite để build. `config/official-client.json` ghim upload Windows miễn phí của tác giả và SHA-256 PCK. `fetch-original-client.py` lấy link tải công khai mới cho mỗi lần chạy, kiểm dung lượng/CRC/SHA và chỉ trích PCK. Không dùng tài khoản itch.io, token cá nhân hoặc URL CDN hết hạn lưu sẵn.

`config/cloud-tools.json` ghim Godot 4.7.2, GDRE 2.7.4, export templates và font theo checksum. `tools/cloud-build-original.py` tự dựng project trong thư mục tạm, áp bản vá offline, từ điển tiếng Việt và addon của dự án, chạy QA rồi xuất client. Khi nguồn tác giả thay đổi, hash không khớp phải dừng để cập nhật có chủ đích; không im lặng dùng game khác phiên bản.

Đây là cơ chế build/mod từ đầu vào chính thức, không phải khẳng định đổi tên tạo quyền phân phối mã/tài nguyên gốc. Giữ ghi công và giấy phép của các thành phần.

## Vòng làm việc từ web

1. Mở repo `ronvotri/rag-svv`, nhánh chứa tài liệu này.
2. Dùng ChatGPT/Claude web để đọc công cụ, bản dịch và addon, rồi yêu cầu thay đổi tính năng cụ thể. Phiên có công cụ GitHub được cấp quyền ghi có thể commit/PR; nếu phiên chỉ có quyền đọc, lấy patch/tệp do chat tạo và cập nhật bằng GitHub web editor.
3. Commit thay đổi trong `original-addons/`, `patches/`, `config/` hoặc helper original sẽ kích hoạt build Windows. Không sửa `engine.js`/`game.js` của prototype cũ để thay đổi client gốc.
4. Vào **Actions → Original client - cloud build**. Khi workflow đã có trên nhánh mặc định, có thể **Run workflow** chọn `windows`, `web` hoặc `android`.
5. Tải artifact `original-offline-<platform>-TEST`. Artifact client test giữ 1 ngày để giảm dung lượng; có thể build lại từ source. `original-client-context` nhỏ chứa các đợt văn bản chưa dịch và danh sách hàm để tiếp tục trong chat web mà không tải cả game.

Việc build do GitHub Actions thực hiện, không cần chat có terminal hoặc phải chạy Codex. Khả năng chat tự ghi GitHub phụ thuộc đúng kết nối và quyền được cấp trong phiên đó; không phải mọi kết nối GitHub trong ChatGPT đều có quyền ghi. Có thể dùng GitHub web editor trên điện thoại làm bước commit khi cần.

## Tệp cần sửa

| Công việc | Vị trí |
| --- | --- |
| Việt hóa giao diện | `patches/vi-ui.json`, `patches/vi-ui-extra.json` |
| NPC hướng dẫn và bộ chọn đội AI | `original-addons/offline_assistant.gd` |
| Chuyển offline và lưu đội bot | `tools/prepare-original-offline.py` |
| Tải đúng client nền | `config/official-client.json`, `tools/fetch-original-client.py` |
| Cài addon và xuất các nền tảng | `tools/install-original-assistant.py`, các helper original/export |
| Build online | `.github/workflows/original-client.yml` |
| Mô hình chat thử nghiệm | `llm.js`, `docs/LOCAL_LLM.md`; chưa nghiệm thu native Godot |

## Điểm chưa hoàn thành

- Việt hóa mới áp dụng 1.106/6.037 mục catalog; nhiều mô tả còn dự phòng Anh/Tây Ban Nha.
- Khôi phục đủ nội dung không chứng minh mọi kỹ năng, boss, tháp, nhiệm vụ và trang bị đều đã nghiệm thu.
- NPC hướng dẫn theo luật không phải LLM; mô hình nhỏ thử trên CPU chưa đạt chất lượng. Không bật mặc định.
- Android output là debug-test, chưa có khóa ký phát hành lâu dài hoặc QA thiết bị.
- Web Godot cần localhost/PWA và kiểm tra cache, không mở trực tiếp file://.
- Quy trình tự tái dựng trên runner Windows target đã đạt; các target web/Android và tính năng còn lại cần lượt kiểm tra riêng.

## Lời nhắn mở chat sau

> Tiếp tục dự án client Midgard gốc offline ở repo ronvotri/rag-svv. Đọc AGENTS.md, docs/ORIGINAL_CLIENT.md và docs/WEB_GITHUB_DEVELOPMENT.md. Giữ sprite Ragnarok, không dùng prototype hình tự vẽ làm game chính. Thực hiện yêu cầu của tôi bằng addon/bản vá, chạy GitHub Actions và báo đúng commit, artifact cùng các giới hạn chưa kiểm tra. Không cần Codex desktop hay ổ E:.
