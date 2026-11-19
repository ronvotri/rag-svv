# Thử nâng nền Midgard Survivors lên v0.2.3 (CHƯA HOÀN TẤT)

Ngày đối chiếu: 19/11/2026.

## Bằng chứng nguồn và rào cản

- [Patch notes chính thức](https://midgardsurvivors.com/news/) ghi `v0.2.3`, ngày 18/11/2026, gồm Wings of Hel, Excalibur rework, điều chỉnh Training Ground, MVP arena và nhiều sửa lỗi.
- [Itch.io phát hành Windows](https://nearq.itch.io/midgard-survivors) vẫn niêm yết `midgard-survivors-windows.zip` nhãn **0.2.0-dx12**, upload ID `20348959` (kiểm tra 19/11).
- Repo `config/official-client.json` đang ghim PCK **0.2.0**: 701913608 bytes, SHA-256 `98992ed1631b1a8a16403776ca2c3e17ad995df402b2b89da616cab9e228f07a`.
- Theo [chính sách kỹ thuật chính thức](https://midgardsurvivors.com/legal/), bản vá mới hơn được Windows tải từ `updates.midgardsurvivors.com` hoặc bản mirror GitHub khi mở game. Bản offline cố ý tắt tự cập nhật, nên không nhận v0.2.3 từ ZIP Windows 0.2.0.
- **KHÔNG được đổi tên version hoặc ghim SHA giả. KHÔNG xác nhận game v0.2.3 khi chưa nhận và kiểm tra byte cập nhật.**

## Quy trình khi đã có gói 0.2.3 đầy đủ / patch chính thức xác minh được

1. Lấy client hoặc bản vá từ kênh chính thức có quyền truy cập. Không đưa gói asset/mã gốc lên repo công khai.
2. Kiểm tra phiên bản thực, byte length, CRC, SHA-256 của bản nền sau vá; ghi rõ archive/upload/source URL không chứa token/hết hạn. Kiểm tra patch chain chính thức có phải các bản cộng dồn hay không. Giữ pin v0.2.0 cho rollback.
3. Trong **nhánh thử nghiệm này**, cập nhật `config/official-client.json` **chỉ nếu** ZIP Windows chứa một PCK mới tương ứng; nếu dùng patch riêng, cần thêm cơ chế tải/kiểm hash/áp patch được kiểm thử, KHÔNG nhét patch binary vào git.
4. Kiểm tra tương thích `prepare-original-offline.py`, `localize_original.py`, addon Mira/Friends List, Save Guardian, 11 Job, các scene mới. Cần QA placeholder/string mới mà không dịch tên item/skill/boss.
5. Chạy Windows build và Web QA; Android QA nếu phát hành APK. Khởi động thật, vào map, đánh quái, Heal, party lưu/tải, Town, NPC, các hệ thống mới 0.2.3.
6. Chỉ merge khi checksum và QA đạt; sau đó mới cân nhắc Cloudflare deploy, không tự triển khai.

## Đang xác minh

- Workflow `upgrade-v023-source-check.yml` kiểm tra lại ZIP công khai, không sửa pin hoặc artifact gốc.
- Nếu upstream vẫn là 0.2.0 thì trạng thái vẫn **BLOCKED — thiếu bản vá 0.2.3 đã xác minh**.
- Bản offline đang có và Save Guardian giữ nguyên, không reset save.

## Phân biệt
Cập nhật gameplay upstream ≠ cập nhật bản dịch ≠ thay giao diện. Batch Việt hóa hiện có và NPC Party không được xóa để nâng phiên bản nền.
