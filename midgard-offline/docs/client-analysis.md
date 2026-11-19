# Kiểm kê client Midgard Survivors cục bộ

Ngày kiểm kê: **15/11/2026**. Mục tiêu: đánh giá cấu trúc client do người dùng cung cấp để định hướng game web offline tiếng Việt. Không chỉnh sửa hoặc chạy client trong đợt kiểm kê này.

## Mẫu đã kiểm tra

Thư mục nguồn: `E:\Game\RagnarokSVV`.

| Tệp | Dung lượng (byte) |
| --- | ---: |
| `MidgardSurvivors.exe` | 109.199.872 |
| `MidgardSurvivors.pck` | 557.227.992 |
| `EOSSDK-Win64-Shipping.dll` | 19.531.704 |
| `libeosg.windows.template_release.x86_64.dll` | 1.144.320 |
| `xaudio2_9redist.dll` | 847.440 |

SHA-256 của PCK:

```text
445a3ed2a0a56cd97bb37ca88efe0a4d7c2e44515acd8e09cba4cd0707cf219e
```

Header có magic `GDPC`, định dạng **PCK v4**, phiên bản engine ghi trong gói là **Godot 4.7.2**. `file_base = 112`; mục lục bắt đầu ở byte `555794464`; cờ gói bằng `2`. Đã đọc thành công **14.387 mục**. Mục lục không mã hóa, và cờ từng tài nguyên đều bằng `0` trong mẫu này. Điều đó chứng minh khả năng kiểm kê tài nguyên của mẫu, chưa chứng minh khả năng khôi phục toàn bộ project.

## Thành phần trong PCK

| Loại | Số mục | Ý nghĩa quan sát được |
| --- | ---: | --- |
| `.import` | 6.114 | Metadata import của Godot |
| `.ctex` | 5.441 | Texture đã qua import |
| `.json` | 1.826 | Các tệp JSON, trong đó có dữ liệu hiệu ứng/sprite |
| `.sample` | 543 | Tài nguyên âm thanh |
| `.remap` | 134 | Ánh xạ tài nguyên xuất |
| `.gdc` | 131 | Script GDScript đã biên dịch |
| `.scn` | 74 | Scene dạng nhị phân |
| `.mp3str` | 55 | Tài nguyên âm thanh đã import |
| `.gat` | 51 | Tệp bản đồ mang đuôi GAT |
| `.po` | 5 | Bảng ngôn ngữ |
| `.fontdata` | 2 | Font đã import |

Những mục khác gồm `.cfg`, `.res`, `.png`, `.bin`, `.gdextension`, `.ico` và `project.binary`. Các con số đếm theo tên mục trong PCK, không phải số đối tượng gameplay độc lập.

Các bảng ngôn ngữ nằm ở `locale/de.po`, `locale/en.po`, `locale/pt.po`, `locale/ru.po`, `locale/zh_TW.po`. Mỗi tệp trong mẫu có **6.038 dòng bắt đầu bằng `msgid `** và **6.014 dòng bắt đầu bằng `msgstr `**. Đây là phép đếm dòng thô, chưa loại comment, header, mục lỗi thời, bản dịch trống hoặc xử lý dạng số nhiều; không dùng làm số lượng khóa cần dịch chính thức. Chưa thấy tệp `locale/vi.po` trong danh mục.

Hai font mang tên `SCDream4.otf` và `SCDream6.otf` đã được import thành `.fontdata`. Chưa kiểm tra bảng glyph, vì vậy chưa thể khẳng định hỗ trợ đầy đủ tiếng Việt chỉ từ tên font.

## Dấu hiệu về phụ thuộc online

Các bằng chứng sau đến từ tên tệp trong thư mục và mục lục, không phải kết quả chạy hoặc giải biên dịch:

- Có DLL EOS và addon `addons/epic-online-services-godot/`, cùng các script `hauth.gdc`, `hlobbies.gdc`, `hp2p.gdc` và `hleaderboards.gdc` trong nhánh `heos/`.
- Có `scripts/net/eos_net.gdc`, `net_sync.gdc`, `town_channel.gdc` và `channel_bot.gdc`.
- Có `scripts/core/cloud_save.gdc`, `friends.gdc`, `leaderboard.gdc`, `trade.gdc`, cùng `scripts/ui/account_window.gdc` và các UI chọn server.
- Có `scripts/autoload/save.gdc` và `scripts/core/run_save.gdc`, cho thấy tên thành phần liên quan lưu cục bộ/lưu lượt bên cạnh cloud save.
- Có `scripts/autoload/updater.gdc` và `scripts/ui/update_window.gdc`.

**Suy luận:** client có cả thành phần chơi/lưu tiến trình và thành phần mạng, tài khoản, cập nhật. Không thể kết luận rằng xóa vài script mạng sẽ tạo ra bản offline đầy đủ. Chưa xác minh chức năng nào bắt buộc có máy chủ, cách xác thực, nơi xử lý kinh tế/trang bị, endpoint đang dùng hoặc hành vi mất mạng.

Tệp `eos/credentials.cfg` xuất hiện trong mục lục. **Không đọc hoặc sao chép nội dung tệp này** trong phân tích; không ghi khóa hoặc thông tin tài khoản vào tài liệu/repo.

## Khả năng khôi phục và hướng hiện tại

Gói có mục lục đọc được nên có cơ sở để khảo sát ngôn ngữ, scene, dữ liệu và tài nguyên cục bộ. Tuy nhiên, script có dạng `.gdc`, scene có dạng `.scn`, cấu hình dự án có dạng `project.binary`, và nhiều ảnh/âm thanh đã qua import. Bộ tệp phát hành này không phải project nguồn có thể chỉnh sửa và xuất web ngay.

Chưa thực hiện giải biên dịch, khôi phục project, kiểm tra plugin trên web, build Godot hoặc kiểm thử client không mạng. Phần máy chủ và cơ sở dữ liệu cũng không được chứng minh là có trong gói.

Theo yêu cầu đã chốt, repo triển khai **web offline độc lập** trong `midgard-offline/`: luật chơi, hình vẽ và giao diện tiếng Việt được xây mới; tiến trình lưu trên trình duyệt. Bản prototype không cần đọc PCK, không sử dụng DLL EOS, tài khoản hoặc máy chủ của client. Đây là nền để phát triển tiếp, chưa phải toàn bộ Midgard Survivors trên web.

## Tái lập kiểm kê

Chạy từ thư mục repo với Python 3.11 trở lên:

```powershell
python midgard-offline/tools/inspect_pck.py "E:\Game\RagnarokSVV\MidgardSurvivors.pck" --output midgard-offline/work/client-inventory.private.json
```

Công cụ kiểm tra giới hạn đường dẫn, vị trí tài nguyên, phiên bản/cờ hỗ trợ và từ chối mục lục mã hóa. Công cụ không ghi đè đầu ra đã có. Thư mục `work/` đã bị `.gitignore` bỏ qua, nên danh mục cục bộ và dữ liệu riêng không tham gia bản build hoặc GitHub.
