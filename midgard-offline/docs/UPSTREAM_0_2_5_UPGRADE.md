# Midgard gốc 0.2.5 và bảo toàn nhánh Cloud

Đối chiếu ngày 21/11/2026: manifest chính thức công bố base Windows 0.2.0,
patch cộng dồn 0.2.5 (20/11/2026). ZIP nền vẫn được ghim độc lập tại
`config/official-client.json`; không đổi hash ZIP thành hash bản vá.

`config/official-update.json` ghim URL, 12.809.900 byte và SHA-256 của patch.
Đã tải thực tế và kiểm tra khớp SHA. Bản vá giải mã là PCK Godot 4.7.2,
169 tài nguyên. Công cụ dùng định dạng của updater gốc đã khôi phục trong
thư mục riêng; không chép khóa hoặc tài nguyên gốc vào Git.

## Thứ tự build

1. Tải và xác minh PCK nền 0.2.0 như trước.
2. Khôi phục nền để đọc định dạng updater; tải patch và kiểm size/SHA.
3. Ghép tài nguyên theo nguyên tắc PCK nạp sau thay mục trùng tên. Kiểm MD5
   từng tài nguyên; từ chối cờ/định dạng chưa hỗ trợ và đầu ra đã tồn tại.
4. Khôi phục PCK đã ghép; áp các bản vá offline, Việt hóa và addon hiện tại.
5. Chạy QA save bằng Godot thật, QA client và xuất artifact. BUILD_STATUS.json
   ghi rõ phiên bản upstream, SHA nền, SHA patch và SHA PCK đã ghép.

Updater lúc chơi vẫn tắt: bản gốc không tự tải đè addon, bản dịch hoặc save.
Tên thư mục dữ liệu và profile offline giữ nguyên để nhận save cũ.

## Nhánh phát triển được giữ

Nhánh nâng cấp tích hợp `feature/offline-friends-wave12-prontera-playtest`
tại `a317c2d` cùng staging kiểm nguồn 0.2.3 tại `1180a06`. Giữ Mira,
Alden/Eira và các quest/bạn đồng hành đã có. Cole/Haneul vẫn theo cổng QA
của nhánh Cloud; không tự mở khóa nội dung đang chờ duyệt.

Không force-push hoặc thay nhánh Cloud bằng cây source gốc. Các PR Wave cũ
vẫn nguyên trạng. Những commit Cloud mới sau mốc trên cần merge tiếp vào
nhánh cập nhật trước khi phát hành. Không đưa game đã khôi phục vào Git.

## Save và kiểm thử

Xem [SAVE_PORTABILITY.md](SAVE_PORTABILITY.md): sửa menu không mở được,
đợi IndexedDB hoàn tất trước khi reload, xác thực nội dung mã hóa trước nhập,
giữ bản dự phòng và hỗ trợ chọn JSON ở Windows. `Save.flush()` chỉ xóa cờ
cần lưu khi ghi/backup/rename thành công; không ghi đè trong giao dịch nhập.
Giữ bộ đếm `save_seq` mới của upstream.

Thử cục bộ dùng bản nền 0.1.273 + bridge chính thức đến 0.2.0 + patch 0.2.5,
tất cả checksum khớp. Khôi phục được 172 script; một chuyển đổi extension EOS
không có thư viện native, addon EOS được bỏ khỏi client offline như trước.
CI dùng trực tiếp ZIP nền 0.2.0 đã ghim, không phụ thuộc ổ E:.

Build/QA đạt không thay cho chơi toàn bộ nội dung mới, thử IndexedDB trên
trình duyệt thật hoặc chuyển save trên điện thoại. Chưa công bố Android hay
triển khai đè trang Web đang chơi chỉ dựa vào test cấu trúc.

Rollback mã: dùng nhánh Cloud trước nâng cấp hoặc revert PR này. Trước khi
chơi bản cũ hơn, xuất JSON save; không giả định upstream hỗ trợ hạ cấp save.

Nguồn: [manifest tác giả](https://raw.githubusercontent.com/Gon-Analista/midgard-survivors-updates/main/manifest.json),
[trang tải chính thức](https://nearq.itch.io/midgard-survivors).
