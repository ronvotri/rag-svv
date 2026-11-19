# Chính sách Việt hóa Midgard SVV Offline (client gốc)

- **Giữ nguyên tiếng Anh**: tên item/trang bị, skill, card/pet và thuật ngữ Ragnarok (HP, SP, ATK, DEF, ASPD, Flee, MVP, Zeny, EXP...). Tên riêng giữ nguyên.
- **Dịch tiếng Việt**: tên nghề (Kiếm Sĩ, Tu Sĩ...), nút, HUD, mô tả item/skill, hướng dẫn, hội thoại NPC, điều kiện nhiệm vụ, thông báo, tutorial, chú giải của tháp. Dịch tự nhiên, dễ đọc và nhất quán.
- Bản dịch được thêm theo các file `patches/vi-ui-batch-*.json`. Mỗi key là tiếng Anh gốc; không tự đoán tên item/skill.
- `localize_original.py` lấy tên gameplay từ `GameData` phục hồi trên runner khi nhận diện được và danh sách `vi-keep-english.json`; các tên đó được giữ tiếng Anh, **kể cả khi từng bị dịch**.
- Giữ nguyên `%d`, `%s`, `%%`, `\n` và biến động runtime; Python kiểm tra placeholder. Không đổi logic gameplay hay dữ liệu lưu.
- Số lượng được dịch vẫn tính từ catalog `locale/en.po` gốc sau mỗi GitHub Actions build; các tên được giữ tiếng Anh không xem là lỗi chưa dịch.
- Các bản dịch mới cần QA tràn chữ trên Web/Android, nhất là thoại dài và cửa sổ vật phẩm. Catalog hiện có 7.309 mục (theo Web QA #265); chưa đánh dấu hoàn tất nếu còn fallback cần người kiểm tra.

**Nhóm đầu tiên:** hướng dẫn, Lucile/Endless Tower, mô tả nghề và một số hiệu ứng; xem file batch 001.

## Rà soát nội dung còn sót

- Báo cáo `untranslated-prose-review.json` được tạo từ client gốc trong mỗi lượt Web QA: lọc những mục tiếng Anh chưa có bản dịch, dài từ 45 ký tự và có từ 8 từ trở lên. Đây là **danh sách nghi vấn**, không tự động dịch tên skill hoặc địa danh.
- Những mục ngắn trong `translation-worklist-*.json` đa phần là tên item, boss, skill, trang bị, nhạc nền hoặc ký hiệu chỉ số cần giữ nguyên. Không dịch chỉ để tăng phần trăm.
- Ngoài catalog phải kiểm tra chuỗi hiển thị bởi `original-addons/` và `cloudflare/`. Web/mobile cần QA ảnh thực tế để phát hiện chữ tràn khung.
- Các chuỗi Việt hóa tiếp theo dùng đúng **khóa English** trong `locale/en.po`, không dùng khóa Tây Ban Nha khi đã có cột English.
