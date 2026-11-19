# Ragnarok client gốc trên Cloudflare Pages Free (không R2)

## Trạng thái

- Người dùng đã tạo site `rag-svv-web.pages.dev` với trang HTML tạm.
- Godot Web export đã PASS một lượt ở [Web QA #43893310727](https://github.com/ronvotri/rag-svv/actions/runs/43893310727), trước khi thêm bộ chia file mới.
- Bộ chia file lớn / Service Worker **phải vượt qua CI mới và QA trình duyệt** trước khi tuyên bố game chạy được; chỉ unit test hoặc xuất Godot không chứng minh Web đầy đủ.
- Công cụ không tải dữ liệu game lên Git. Nó nhận bản export mới ở runner, chia file, đóng gói website. Website hiện tại vẫn là trang tạm cho tới khi có một lần phát hành thật hợp lệ.
- **Quyền tài nguyên:** tải được client gốc không đồng nghĩa có quyền phân phối công khai sprite/mã game. Workflow vẫn yêu cầu người chạy xác nhận được phép phát hành. Nếu chưa có, không upload bản game gốc lên website công khai.

## Vì sao không cần R2?

Cloudflare Pages Free hỗ trợ file đơn tối đa **25 MiB**, website tối đa **20.000 file**, theo https://developers.cloudflare.com/pages/platform/limits/.
Godot Web tạo `.pck` và `.wasm` lớn hơn 25 MiB; uploader trực tiếp không nhận các file đó.

`tools/prepare-original-web-deploy.py` sẽ:

1. Giữ `game.html` (HTML export gốc), JS/CSS/hình nhỏ.
2. Đổi `index.html` thành trang chờ khởi động Service Worker, sau đó mới chuyển đến `game.html`.
3. Chia file lớn thành các phần tĩnh tối đa **16 MiB** ở `parts/<git-commit>/<tên file>/0000.bin`.
4. Sinh `asset-map.json` có danh sách phần, kích thước và SHA-256 được tính từ file gốc.
5. Cài `godot-split-sw.js` vào thư mục Pages. Service Worker của **trình duyệt** bắt yêu cầu tải URL `index.pck` và `index.wasm`, trả một `ReadableStream` ghép từng phần theo đúng thứ tự, có hỗ trợ Range, đúng Content-Type cho WASM. Không cần sửa Godot loader hoặc gọi Cloudflare Workers/R2.
6. Kiểm tra số lượng file, dung lượng mỗi file trước khi xuất bản.

Giới hạn: chia nhỏ không giảm tổng dung lượng game hoặc nhu cầu RAM của Godot; tải nhiều phần liên tiếp vẫn có thể chậm. Save cục bộ của Godot vẫn nằm theo site/browser, không tự đồng bộ máy khác. Ngắt mạng giữa lần tải đầu tiên có thể ngăn vào game; chưa được xem là một PWA có bộ cài offline đầy đủ.

## Chỉ cần 2 GitHub Secrets (không cần R2)

Trang Pages `rag-svv-web` đã được khởi tạo bằng Direct Upload và có thể cập nhật bằng Wrangler qua GitHub Actions.

1. Cloudflare → API Tokens: https://dash.cloudflare.com/?to=/:account/api-tokens
   - Tạo token có quyền **Account / Cloudflare Pages / Edit** chỉ cho tài khoản phù hợp.
2. Cloudflare Dashboard → Account home / R2 Overview / Account Details để lấy **Account ID** (không phải API token).
3. GitHub Secrets: https://github.com/ronvotri/rag-svv/settings/secrets/actions
   - `CLOUDFLARE_ACCOUNT_ID`: Account ID của Cloudflare
   - `CLOUDFLARE_API_TOKEN`: token chỉ dành cho Pages

Không cần `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, bucket R2, đăng ký R2 hoặc bật thanh toán cho R2.

**Không gửi token vào chat, commit hay ảnh chụp.** Chỉ nhập vào GitHub Secrets.

## Xuất bản

Sau khi kiểm tra việc có quyền phân phối game gốc, mở workflow:
https://github.com/ronvotri/rag-svv/actions/workflows/original-web-publish.yml

- Chọn **Run workflow**, nhánh **main** (workflow được cài ở đây).
- Chỉ tích `redistribution_rights_confirmed` nếu bạn thực sự có quyền phân phối tài nguyên gốc.
- Workflow tự checkout `feature/original-offline`, rebuild Godot trên runner, chạy Python/Node test, đóng gói các phần file tĩnh, gọi Wrangler để deploy `public/` lên project `rag-svv-web`.
- Workflow đọc `production_branch` của Pages project bằng Cloudflare API, tránh deploy nhầm lên nhánh preview.
- Không cần tải file .pck lên tay và không có bước upload R2. Không kích hoạt workflow nếu chưa xác nhận quyền phát hành.

## Tiêu chí nghiệm thu website

- Mở https://rag-svv-web.pages.dev và chờ chuyển trang từ `index.html` sang `game.html`.
- F12 → Network: `asset-map.json`, `godot-split-sw.js` và các URL `parts/<sha>/...` tải HTTP 200; URL `index.wasm` được Service Worker trả `application/wasm`. Không có request đến R2.
- Sau khi tải đủ, Godot hiện màn chọn nhân vật, không yêu cầu login; sprite, âm thanh, NPC, AI chiến đấu hoạt động.
- Reload; xác nhận save/đội đồng hành cục bộ còn nguyên; kiểm tra cả Chrome/Edge desktop và Chrome Android.
- Có hiển thị lỗi dễ hiểu nếu HTTPS/Service Worker không hoạt động, một phần file bị thiếu, hoặc thiết bị không đủ bộ nhớ.
- Có quyền phát hành asset gốc trước khi mở bản Web cho mọi người.

## Mã nguồn

- `tools/prepare-original-web-deploy.py`: chia file và kiểm tra giới hạn Pages.
- `cloudflare/pages-bootstrap.html`: HTML chuẩn bị Service Worker và chuyển vào Godot.
- `cloudflare/godot-split-sw.js`: ghép từng phần trên trình duyệt bằng stream, không tốn Worker quota.
- `tests/test_original_web_deploy.py`: kiểm tra chia đúng, hash và lỗi đầu vào.
- `tests/original-web-loader.test.cjs`: mô phỏng stream/HTTP Range/missing chunk.
- `.github/workflows/original-web-qa.yml`: chạy QA không xuất bản.
- `.github/workflows/original-web-publish.yml`: thủ công, yêu cầu xác nhận quyền và đủ 2 secret Pages.
