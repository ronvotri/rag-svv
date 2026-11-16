# Chơi Ragnarok client gốc trên website (Cloudflare Pages + R2)

## Trạng thái thực tế

- Godot Web export QA đã **PASS** ở workflow [43887959854](https://github.com/ronvotri/rag-svv/actions/runs/43887959854), commit `a9a089f`. Đây là xác nhận **xuất gói Web**, không phải đã chơi thử trên thiết bị.
- Chưa có tên miền chơi công khai được xác minh. Không gọi website là đang hoạt động trước khi Cloudflare deploy thành công và qua QA trình duyệt.
- Game được xây dựng lại trên GitHub Actions từ bản game chính thức rồi vá offline. Source game và sprite gốc **không được lưu trong repository công khai**.
- **Quan trọng về bản quyền:** workflow chỉ công bố asset sau khi chủ tài khoản chủ động xác nhận có quyền phân phối lại tài nguyên gốc. Có bản game tải về để chơi không mặc nhiên đồng nghĩa được quyền phát hành công khai. Nếu chưa có quyền, chỉ chạy bản Web riêng tư cục bộ và xin phép tác giả/nhà phát hành.

## Kiến trúc

```text
Trình duyệt (không login)
   |
   v
Cloudflare Pages: HTML, JavaScript, giao diện, file nhỏ
   |
   +-- Godot file > 25 MiB --> Pages Function
                                    |
                                    v
                                R2 bucket riêng
                                releases/<git-sha>/<name>
```

- **Cloudflare Pages**: file tĩnh nhỏ hơn hoặc bằng 25 MiB và URL website.
- **Cloudflare R2**: file `.pck`, `.wasm` hoặc tệp khác lớn hơn 25 MiB. Không bật public bucket. Pages Function đọc binding `GAME_ASSETS` và trả file tại **đúng URL gốc** (`/index.pck`, `/index.wasm`) nên Godot không cần sửa loader.
- `_routes.json` chỉ chuyển URL tệp lớn vào Function; file nhỏ phục vụ trực tiếp từ CDN.
- Thay đổi commit tạo khóa `releases/<sha>/`, tránh đè nội dung của những bản đang mở.
- Lưu trữ `profile_offline` dùng `user://` của Godot trong browser, phụ thuộc vùng dữ liệu website trên thiết bị. Save Guardian có hai bản cục bộ nhưng **không đồng bộ cloud**. Xóa dữ liệu website, duyệt riêng tư hoặc đổi máy có thể mất save. Việc bổ sung xuất/nhập save vẫn là đầu việc riêng.

## Thiết lập Cloudflare một lần

1. Đăng nhập Cloudflare và tạo **Pages project** tên chính xác `rag-svv-web` (Direct Upload / Wrangler). Không chọn pipeline Web prototype HTML.
2. Tạo **R2 bucket** tên `rag-svv-game-assets`; có thể để private. Bản đóng gói dùng binding `GAME_ASSETS` khai báo qua `wrangler.toml`.
3. Tạo **API Token** Cloudflare đủ quyền cập nhật Pages của account.
4. Tạo **R2 API token** giới hạn quyền Object Read & Write của bucket trên; lấy Access Key ID và Secret Access Key theo hướng dẫn R2.
5. Trong GitHub `ronvotri/rag-svv` → Settings → Secrets and variables → Actions, thêm **bốn secret**:

| GitHub secret | Nội dung |
| --- | --- |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare Account ID |
| `CLOUDFLARE_API_TOKEN` | Token sửa Pages |
| `R2_ACCESS_KEY_ID` | R2 Access Key ID |
| `R2_SECRET_ACCESS_KEY` | R2 Secret Access Key |

6. Trong GitHub → Actions → **Ragnarok SVV - publish original Web (Cloudflare)** → Run workflow, chọn nhánh `main`, tích ô `redistribution_rights_confirmed` **chỉ nếu có quyền phát hành tài nguyên gốc**. Workflow sẽ tự checkout `feature/original-offline`, dựng Godot, chạy test, chuyển file lớn lên R2 rồi deploy Pages.
7. Kiểm tra deployment URL do Cloudflare trả về. Với project tên này, hostname mặc định dự kiến là `rag-svv-web.pages.dev`, **không phải URL đã xác minh là đang chạy**.

**Không bao giờ** điền token vào chat, file Git hoặc giao diện game. Chỉ cấu hình vào GitHub Secrets.

## Đã thêm trong repo

- `tools/prepare-original-web-deploy.py`: chia file Pages/R2 an toàn với ngưỡng 25 MiB; sinh `_routes.json`, `wrangler.toml`, manifest SHA-256.
- `cloudflare/functions/[[path]].js`: trả file lớn qua binding R2 cùng origin, hỗ trợ HEAD và byte range.
- `tests/test_original_web_deploy.py`: thử với các fixture nhỏ, xác minh tệp lớn không lọt vào Pages.
- `.github/workflows/original-web-publish.yml`: **chỉ manual**, xác nhận quyền phát hành, không tự upload tài nguyên chỉ vì push GitHub.

## Kiểm thử trước khi gọi là hoàn thành

- URL mở `index.html`, các file Godot JS/WASM/PCK tải HTTP 200 và Content-Type đúng (WASM: `application/wasm`).
- Mở game và vào màn chọn nhân vật **không login**, thử chiến đấu, AI đồng hành, menu tiếng Việt, không thiếu sprite.
- Save: kết thúc lượt, reload website, kiểm tra hồ sơ/đội hình/Guardian vẫn còn. Mở ở Safari/Chrome Android để kiểm tra cục bộ.
- Đo tốc độ tải và bộ nhớ: Web package hiện đã lớn ~507 MB **sau nén**; chạy trên điện thoại có nguy cơ chậm/hết bộ nhớ. Cần tối ưu thêm asset để có trải nghiệm tốt.
- Kiểm tra gửi file byte range, Cache-Control, deployment cũ/mới và giới hạn tài nguyên; tránh thông báo website đã sẵn sàng nếu chỉ CI build pass.
