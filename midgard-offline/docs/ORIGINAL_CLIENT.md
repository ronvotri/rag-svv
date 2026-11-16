# Client Midgard gốc offline

Mục tiêu đã chốt: **giữ sprite Ragnarok, bản đồ, kỹ năng và hệ thống của client do người dùng cung cấp**, chuyển sang chơi offline, thêm đồng đội AI và hội thoại. Web/Windows/Android là các bản xuất từ nền này. Prototype HTML/JS tự vẽ trong thư mục cha không phải client gốc và không phải bản bàn giao cho mục tiêu này.

## Dữ liệu và project cục bộ

- Nguồn chỉ đọc: `E:\Game\RagnarokSVV`, bản 0.1.273, Godot 4.7.2.
- GDRE 2.7.4 đã khôi phục 131/131 script và 6.249 tài nguyên; có 595 chuyển đổi lossy từ dữ liệu phát hành đã nén. Không hứa khôi phục nguyên vẹn nguồn của tác giả.
- `work/recovered/`: project phục hồi để tham chiếu.
- `work/recovered-offline/`: bản riêng được vá offline. Mọi thay đổi và bản build từ dữ liệu gốc giữ trong `work/`, không push lên GitHub công khai.
- `work/screenshots/original-town.png` và `original-combat.png`: ảnh chụp render thật từ project Godot, có Prontera, sprite Ragnarok, quái và đội bot. Đây là bằng chứng cảnh đã chạy, chưa phải nghiệm thu toàn bộ game.

Kiểm kê dictionary tĩnh của client: 11 nghề, 20 màn, 349 mục kỹ năng, 163 thẻ, 209 vật phẩm, 46 pet, 20 nhiệm vụ, 73 thành tựu. Các biến thể/hỗ trợ có thể cùng nằm trong các dictionary này; không dùng số đếm thay kiểm thử hành vi.

## Các phần vá tự viết

`prepare-original-offline.py` tạo bản riêng, tách `profile_offline` khỏi game gốc, vô hiệu hóa EOS/tài khoản, cloud save, cập nhật, bảng xếp hạng mạng và kết nối tổ đội/kênh. Thị trấn/NPC và gameplay cục bộ được giữ. Đồng đội dùng `HeroInput.BotHero` của game, với bộ chọn đội bổ sung; không dùng cờ test `--coop` làm chế độ chơi chính.

Helper cũng bổ sung snapshot đội bot cho lưu tiếp trận. QA dùng `--offline-test`, profile và snapshot test riêng. Chỉ báo lưu/khôi phục thành công sau khi bài kiểm tra runtime kiểm tra máu, cấp, đồng hồ và đội hình thực tế.

`install-original-assistant.py` cài overlay tự viết trong `original-addons/`: chọn tối đa ba nghề đồng hành và hỏi hướng dẫn NPC theo tình huống. Hộp thoại theo luật được ghi rõ, không giả là mô hình ngôn ngữ lớn. Overlay không cấp vật phẩm hoặc sửa chỉ số thông qua nội dung trò chuyện.

`localize_original.py` ghép các từ điển tiếng Việt tự viết, giữ placeholder và tạo `locale/vi.po` trong project riêng. Mốc đã áp dụng: **1.106/6.037 mục catalog**, 4.908 mục dự phòng tiếng Anh và 23 mục dự phòng ngôn ngữ nguồn; đây chưa phải Việt hóa hoàn chỉnh. Nhiều mục còn lại là tên riêng, nhưng mô tả và lời thoại cũng còn cần dịch/rà soát. Font Noto Sans Regular/Bold có OFL, đã kiểm tra đủ glyph tiếng Việt và giữ giấy phép trong tài nguyên project.

## Kiểm tra trước bàn giao

- Khởi động và chọn nhân vật; cảnh Prontera, quái, sprite/animation, bản đồ và âm thanh không thiếu tài nguyên.
- Chiến đấu thật với người chơi cùng bot, tăng cấp, tiến hóa/chuyển nghề và nhận thưởng đúng.
- Lưu/khôi phục cả đội; không nhân đôi thưởng hoặc mở lại lượt đã kết thúc.
- Kho, rèn/khảm, thẻ, pet, nhiệm vụ, tái sinh, tháp và các sự kiện phải có đường thao tác thực tế được kiểm tra.
- Dịch còn thiếu và UI không tràn/che HUD. Phần online bị vô hiệu phải có nhãn/trạng thái offline rõ ràng.
- Windows: xuất EXE/PCK và chạy bản xuất, không chỉ chạy trong editor.
- Web: WASM/PCK cần localhost hoặc PWA; không hứa mở trực tiếp `file://`. Kiểm tra lưu, cache và chơi sau khi ngắt mạng.
- Android: APK native Godot giữ tài nguyên gốc; cần kiểm tra thiết bị, cảm ứng, hiệu năng và save. Bản debug chưa phải bản phát hành có danh tính ký lâu dài.
- LLM: suy luận Node đã chạy nhưng chất lượng Qwen 0,5B chưa đạt; chưa có nghiệm thu LLM trong client Godot native. Không ghi full AI chat chỉ vì có gói mô hình tùy chọn.

Các kết quả trên phải được cập nhật theo artifact/bài kiểm tra thực tế. Chưa coi mục tiêu đầy đủ tính năng, hoàn toàn Việt hóa và AI trên cả ba nền tảng là hoàn thành chỉ dựa trên phục hồi source hoặc số tệp đã build.
