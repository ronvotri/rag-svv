# Chính sách Việt hóa Midgard SVV Offline (client gốc)

- **Giữ nguyên tiếng Anh**: tên item/trang bị, skill, card/pet và thuật ngữ Ragnarok (HP, SP, ATK, DEF, ASPD, Flee, MVP, Zeny, EXP...). Tên riêng giữ nguyên.
- **Dịch tiếng Việt**: tên nghề (Kiếm Sĩ, Tu Sĩ...), nút, HUD, mô tả item/skill, hướng dẫn, hội thoại NPC, điều kiện nhiệm vụ, thông báo, tutorial, chú giải của tháp. Dịch tự nhiên, dễ đọc và nhất quán.
- Bản dịch được thêm theo các file `patches/vi-ui-batch-*.json`. Mỗi key là tiếng Anh gốc; không tự đoán tên item/skill.
- `localize_original.py` lấy tên gameplay từ `GameData` phục hồi trên runner khi nhận diện được và danh sách `vi-keep-english.json`; các tên đó được giữ tiếng Anh, **kể cả khi từng bị dịch**.
- Giữ nguyên `%d`, `%s`, `%%`, `\n` và biến động runtime; Python kiểm tra placeholder. Không đổi logic gameplay hay dữ liệu lưu.
- Số lượng được dịch vẫn tính từ catalog `locale/en.po` gốc sau mỗi GitHub Actions build; các tên được giữ tiếng Anh không xem là lỗi chưa dịch.
- Các bản dịch mới cần QA tràn chữ trên Web/Android, nhất là thoại dài và cửa sổ vật phẩm. Chưa đánh dấu toàn bộ 6.037 chuỗi hoàn tất nếu catalog còn fallback.

**Nhóm đầu tiên:** hướng dẫn, Lucile/Endless Tower, mô tả nghề và một số hiệu ứng; xem file batch 001.
