# Nguồn client chính thức cho build cloud

Repo công khai chỉ cần chứa công cụ, bản dịch và patch do dự án viết. Bước build có thể tự tải client miễn phí từ trang chính thức của tác giả, kiểm tra đúng bản nền rồi khôi phục trong thư mục tạm. Không cần ổ `E:`, máy Windows ban đầu, tài khoản itch.io hoặc API key.

## Nguồn và bằng chứng

- Trang chính thức: [nearQ — Midgard Survivors](https://nearq.itch.io/midgard-survivors).
- Upload Windows đang công khai: ID `20348959`, tên `midgard-survivors-windows.zip`, nhãn `0.1.275-dx12`.
- ZIP: `534365028` byte. Thành viên `MidgardSurvivors.pck`: `557227992` byte, CRC-32 `dbfe3e91`.
- PCK cục bộ được dùng khôi phục bản nền `0.1.273` có cùng dung lượng và CRC-32; SHA-256 đã biết là `445a3ed2a0a56cd97bb37ca88efe0a4d7c2e44515acd8e09cba4cd0707cf219e`.

Ngày kiểm tra metadata: **16/11/2026**. Đã thực hiện yêu cầu công khai ẩn danh thành công và chỉ tải **128 KiB cuối ZIP** để kiểm tra mục lục. Dung lượng và CRC trùng với PCK cục bộ là bằng chứng mạnh, nhưng chưa thay cho SHA-256 của toàn bộ PCK từ lần tải mới. Bước tải đầy đủ trong CI phải xác minh SHA này trước khi chấp nhận client.

URL CDN được itch.io tạo mới cho mỗi phiên và hết hạn; không lưu URL đó vào repo. Script dùng cookie ẩn danh và trường CSRF của trang công khai, như chính nút tải miễn phí. Không đăng nhập, không mua hàng và không vượt paywall. Nếu trang không còn miễn phí, upload biến mất hoặc byte/hash thay đổi, script dừng để rà soát thay vì lấy bản mới một cách im lặng.

## Lệnh cho GitHub Actions hoặc ChatGPT web

Yêu cầu Python 3.11 trở lên, chỉ thư viện chuẩn. Từ thư mục repo:

```text
python midgard-offline/tools/fetch-original-client.py --metadata
python midgard-offline/tools/fetch-original-client.py --output midgard-offline/work/client/MidgardSurvivors.pck
```

Lệnh đầu chỉ kiểm metadata. Lệnh thứ hai tải ZIP tạm, kiểm CRC **mọi thành viên**, chỉ giải nén PCK đã ghim và xác minh SHA-256. Không giải nén/chạy EXE hoặc DLL. ZIP tạm được dọn sau khi xong; đầu ra dưới `work/` bị Git bỏ qua.

Nếu đã có ZIP tải chính thức:

```text
python midgard-offline/tools/fetch-original-client.py --archive path/to/midgard-survivors-windows.zip --output midgard-offline/work/client/MidgardSurvivors.pck
```

Đầu ra đã tồn tại chỉ được dùng lại khi đúng dung lượng và SHA đã ghim. Tệp sai không bị ghi đè. Kiểm thử archive giả nhỏ, không cần mạng:

```text
python midgard-offline/tests/test_fetch_original_client.py
```

Sau khi lấy đúng PCK, workflow tiếp tục dùng công cụ khôi phục và áp patch trong repo. Có nguồn tải miễn phí không đồng nghĩa được phép đưa nguyên tài sản/mã khôi phục của game lên GitHub công khai; công cụ này chỉ phục vụ bước chuẩn bị đầu vào. Không dùng patch cập nhật `0.1.280` thay cho client nền đầy đủ vì patch đó thiếu phần lớn tài nguyên.
