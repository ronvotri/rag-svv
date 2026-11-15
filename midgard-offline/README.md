# Biên niên Midgard — web offline tiếng Việt

Một game sinh tồn chơi đơn được xây riêng bằng HTML, CSS, JavaScript và Canvas. **Bản hiện tại là prototype 0.1**, có một vòng chơi từ chọn nghề đến kết quả trận và rèn luyện. Chưa phải bản chuyển đổi đầy đủ hoặc bản clone 1:1 của Midgard Survivors.

## Chạy trên máy

1. Tải hoặc clone repo, giữ nguyên các tệp trong `midgard-offline/`.
2. Mở `index.html` bằng Chrome, Edge hoặc Firefox hiện đại.
3. Chọn nghề, chọn khu vực đã mở khóa rồi nhấn **Bắt đầu hành trình**.

Không cần cài thư viện, đăng nhập, kết nối mạng hoặc có client `E:\Game\RagnarokSVV`. Trình duyệt đọc các tệp nằm cạnh `index.html`; mã game không gọi API bên ngoài, CDN, font mạng hay dịch vụ lưu đám mây. Có thể ngắt Internet trước khi mở để kiểm tra tính offline.

Nếu muốn phục vụ qua HTTP cục bộ khi phát triển, chạy từ thư mục repo:

```powershell
python -m http.server 8765 --bind 127.0.0.1 --directory midgard-offline
```

Sau đó mở `http://127.0.0.1:8765/`. Đây là máy chủ tệp trên chính máy bạn, không phải máy chủ gameplay. Cách mở trực tiếp `index.html` vẫn là lựa chọn không cần chạy máy chủ.

## Cách chơi

| Thao tác | Điều khiển |
| --- | --- |
| Di chuyển | WASD hoặc phím mũi tên |
| Tấn công | Tự động khi có kẻ địch trong tầm |
| Lướt né | Space khi đang di chuyển; hồi chiêu 3 giây |
| Tạm dừng / tiếp tục | Escape, P hoặc nút tạm dừng |
| Chọn nâng cấp | Nhấn một trong ba thẻ khi lên cấp |

Trên màn hình cảm ứng, dùng cần di chuyển ảo và nút **Lướt**.

Nhặt tinh thể kinh nghiệm do quái để lại để lên cấp. Các đợt quái mạnh dần; **Vua Cổ Thụ** xuất hiện khi đồng hồ đạt **05:00**. Hạ boss để thắng. Nếu hết máu hoặc chưa thắng khi đạt **07:00**, lượt chơi kết thúc thất bại. Cả thắng và thua đều có thể nhận vàng tùy thời gian sống sót và số quái đã hạ.

### Nghề nghiệp và khu vực

| Nghề | Lối chơi |
| --- | --- |
| Kiếm sĩ | Nhiều máu, chém lan quanh người |
| Cung thủ | Di chuyển nhanh, bắn xa, mũi tên có thể xuyên quái |
| Pháp sư | Cầu lửa gây sát thương vùng |

**Đồng cỏ bình minh** mở từ đầu. **Rừng sương cổ** mở sau một chiến thắng, **Phế tích hoàng hôn** mở sau hai chiến thắng. Bản đồ sau có độ khó cao hơn.

Chín loại nâng cấp trong trận gồm sát thương, tốc độ đánh, sức sống, di chuyển, tầm nhặt kinh nghiệm, vệ tinh lửa, vòng băng, hồi phục và dư ảnh. Nâng cấp trong trận được đặt lại khi bắt đầu lượt mới.

Vàng dùng tại **Rèn luyện** để tăng vĩnh viễn thể lực, võ nghệ và lượng vàng nhận được. Mỗi nhánh có tối đa 10 bậc; chi phí tăng theo bậc.

## Dữ liệu lưu

Game lưu vàng, bậc rèn luyện và thống kê lượt chơi trong bộ nhớ trình duyệt trên thiết bị đang dùng. **Không tự đồng bộ giữa máy hoặc giữa các trình duyệt.** Lượt chiến đấu đang diễn ra không phải bản lưu để tiếp tục sau khi đóng trang.

- Nhấn **Xuất lưu** để tải JSON làm bản sao dự phòng hoặc mang sang máy khác.
- Nhấn **Nhập lưu** để chọn tệp JSON đã xuất. Việc nhập thay thế tiến trình hiện tại bằng nội dung của tệp.
- Nên xuất lưu trước khi đổi vị trí thư mục game, đổi trình duyệt hoặc xóa dữ liệu duyệt web. Hành vi lưu với `file://` phụ thuộc trình duyệt và đường dẫn tệp.
- Chế độ riêng tư hoặc chính sách chặn lưu trữ có thể khiến tiến trình không được giữ sau khi đóng trình duyệt; sử dụng Xuất lưu để giữ bản sao.

## Tiếp tục trên cloud hoặc máy khác

Mã nguồn mới nằm hoàn toàn trong repo. Có thể clone repo vào môi trường Codex cloud hoặc máy phát triển khác; không cần truy cập ổ `E:` trên máy gốc để phát triển và build bản web này.

Yêu cầu kiểm tra và build: **Node.js 20 trở lên**, không có gói npm phải tải thêm.

```powershell
node --test midgard-offline/tests/*.test.cjs
node midgard-offline/tools/build.mjs
```

Công cụ build tạo gói ZIP chứa các tệp chơi offline. Có thể chuyển ZIP sang máy khác, giải nén rồi mở `index.html`. Workflow trong **GitHub Actions** chạy kiểm tra và cung cấp artifact bản build khi được kích hoạt theo cấu hình của repo. Vào tab **Actions**, mở lượt chạy thành công và tải phần **Artifacts**. Máy chạy Actions cần mạng để lấy repo; bản game tải về chơi độc lập không cần mạng.

Đầu ra cụ thể: `midgard-offline/dist/midgard-offline-0.1.0.zip` và `SHA256SUMS.txt`. Khi giải nén trên Windows, có thể nhấn `CHOI_GAME.cmd` để mở game. Trong Codex Cloud, chọn repo `ronvotri/rag-svv` cùng nhánh chứa `midgard-offline/`; yêu cầu chỉnh game, chạy hai lệnh trên rồi commit/push thay đổi. Không cần setup script cài thư viện. Những thay đổi chỉ còn trên máy cục bộ chưa có trên cloud cho tới khi được push lên GitHub.

Ví dụ lời nhắn cho phiên cloud tiếp theo: “Tiếp tục game web offline tiếng Việt trong `midgard-offline/`. Đọc `AGENTS.md` và README, kiểm tra trạng thái code hiện có, sửa tính năng tôi yêu cầu, chạy tests và build ZIP. Giữ khả năng chơi khi mở file trực tiếp và không thêm phụ thuộc online.”

Thư mục `work/` chứa kiểm kê client cục bộ và đã bị Git bỏ qua. Các dữ liệu này không được dùng trong quá trình build web. Việc tiếp tục phân tích client gốc trên cloud cần cung cấp tệp cục bộ riêng trong môi trường đó; không đưa PCK hoặc tệp game lên repo công khai.

## Kiểm kê client Godot tùy chọn

Python 3.11 trở lên, chỉ dùng thư viện chuẩn:

```powershell
python midgard-offline/tools/inspect_pck.py "E:\Game\RagnarokSVV\MidgardSurvivors.pck"
```

Đầu ra mặc định là `midgard-offline/work/client-inventory.private.json`. Nếu đã có đầu ra, chọn tên khác bằng `--output` để giữ bản kiểm kê cũ. Công cụ chỉ đọc header, mục lục và tính hash; không trích tài nguyên, giải mã, đọc khóa đăng nhập hay chạy script của game.

Đọc [phân tích client](docs/client-analysis.md) để phân biệt bằng chứng đã thu được với những phần chưa xác minh. Bản thử nghiệm chưa bao gồm toàn bộ nghề, trang bị, thẻ, bản đồ, cốt truyện và hệ thống của game tham chiếu. Cân bằng độ khó và kiểm thử nhiều thiết bị vẫn cần tiếp tục trước một bản phát hành hoàn chỉnh.
