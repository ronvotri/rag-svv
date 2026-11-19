# Build online đã xác minh

Ngày: **16/11/2026** (Asia/Saigon).

- Repo: [ronvotri/rag-svv](https://github.com/ronvotri/rag-svv).
- Nhánh tiếp tục: `feature/original-offline`.
- Commit được build: `f4262bbbc43dedfb7102637287d62cfabb2e32a4`.
- [GitHub Actions run 43785523181](https://github.com/ronvotri/rag-svv/actions/runs/43785523181): **success**.
- [PR #2](https://github.com/ronvotri/rag-svv/pull/2): công cụ và thay đổi cho client gốc, không phải prototype hình tự vẽ.

Runner Linux đã tự tải các công cụ chính thức và client nền từ itch.io, xác minh SHA-256 PCK, khôi phục source/tài nguyên, áp patch offline/tiếng Việt/đồng đội, chạy QA và xuất Windows EXE/PCK. Không dùng ổ E:, SDK trên máy cá nhân hoặc ứng dụng Codex desktop.

Artifact `original-offline-windows-TEST` **527.135.760 byte**, ID `14190128939`, đã upload thành công. SHA-256 outer artifact ZIP: `c83d919c1aa26745f0bee3ef7fbbbd6f5ea52198996064b2f798e45b9b444595`. Tải từ phần Artifacts của lượt chạy, giải nén gói client bên trong và mở EXE cùng PCK đi kèm. Bản test được giữ 1 ngày; có thể build lại từ source sau khi hết hạn.

Artifact nhỏ `original-client-context`, ID `14190173692`, **188.296 byte**, giữ 7 ngày, chứa danh sách hàm và các đợt văn bản chưa dịch để tiếp tục trong chat web. Không cần tải hơn 500 MB chỉ để làm phần bản dịch.

## Phạm vi đã xác minh

- 43 tests Node cho phần tự viết, 8 tests Python cho đầu vào/đóng gói đạt.
- QA runtime source gốc kiểm tra dữ liệu, khởi động, chiến đấu người + ba bot, lưu/khôi phục đội và tiến trình nhân vật. Bài test buộc trả mã lỗi khi có lỗi; pipeline đã đi tiếp tới export và upload.
- Cảnh Prontera và chiến đấu với sprite Ragnarok thật đã được render cục bộ; bản EXE/PCK cục bộ khởi động độc lập thành công.
- Lần tải mới trên runner đã đi qua kiểm SHA PCK, không chỉ so dung lượng/CRC metadata.

## Chưa hoàn thành

Việt hóa đầy đủ, nghiệm thu mọi kỹ năng/boss/tháp/trang bị, chat LLM native chất lượng tốt, build/QA web và Android, khóa ký Android lâu dài, kiểm tra thiết bị và hiệu năng. Thành công Windows CI không thay thế các mục này. Người dùng đã chọn chuyển phần phát triển còn lại sang workflow web/GitHub để giảm phụ thuộc máy và tín dụng.

Chat web có công cụ GitHub được cấp quyền ghi có thể sửa/commit trực tiếp; phiên chỉ đọc dùng patch/tệp cùng GitHub web editor. Build chạy trên GitHub Actions trong cả hai trường hợp, không yêu cầu ứng dụng Codex desktop.
