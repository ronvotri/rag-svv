# Phạm vi tính năng và tiêu chí hoàn thiện

Ngày kiểm kê: 15/11/2026. Mốc đối chiếu mã web: prototype 0.1 trước đợt mở rộng đa nền tảng. Bảng này là danh sách kiểm tra, **không phải tuyên bố đã đạt ngang bản gốc**. Các thay đổi sau mốc đó phải được xác nhận bằng test và bản build cụ thể trước khi đổi trạng thái.

## Nguồn và độ chắc chắn

- [Website chính thức](https://midgardsurvivors.com/) công bố 11 nghề gốc, 20 bản đồ, 24 MVP, hơn 160 thẻ, chuyển nghề/tái sinh, kỹ năng tự động/tiến hóa, tháp và co-op. Phần online có thành phố, tổ đội và trao đổi. Đây là phạm vi quảng bá hiện tại; chưa xác nhận mọi con số đều trùng client đang có.
- Client cục bộ: `MidgardSurvivors.pck`, SHA-256 `445a3ed2a0a56cd97bb37ca88efe0a4d7c2e44515acd8e09cba4cd0707cf219e`, Godot 4.7.2, PCK v4, 14.387 mục. Xem [kiểm kê client](client-analysis.md).
- Tên script và nhãn ngôn ngữ xác nhận dấu hiệu của nhiều hệ thống phụ. Tên tệp chứng minh thành phần tồn tại, chưa chứng minh toàn bộ luật, công thức, độ cân bằng hoặc phụ thuộc máy chủ.
- [Roadmap chính thức](https://midgardsurvivors.com/vision/) có hạng mục tương lai; không tự coi roadmap là tính năng đã phát hành trong mẫu cục bộ.

## Danh sách đối chiếu

| Hệ thống | Bằng chứng gốc | Mốc web 0.1 | Tiêu chí nghiệm thu bản offline |
| --- | --- | --- | --- |
| Nghề và nhánh chuyển nghề | Website; `game_data.gdc`, `player.gdc`; nhãn nghề trong locale | 3 nghề tự xây | Mọi nghề mục tiêu chọn/chơi được; nhánh nghề có tác động riêng và điều kiện mở rõ ràng |
| Cấp nhân vật, thuộc tính, cấp nghề | `player.gdc`, `ro_status_window.gdc`, nhãn Base/Class Lv | Cấp trong trận + 3 nhánh rèn luyện | Cấp, chỉ số, lưu và tăng trưởng nhất quán; chuyển nghề không mất dữ liệu sai |
| Kỹ năng tự động, nội tại, tiến hóa | Website; `skills.gdc`, `dots.gdc`, `status_marks.gdc` | 3 kiểu đánh + 9 nâng cấp | Phân biệt active/passive, điều kiện tiến hóa, sát thương/trạng thái và giới hạn |
| Bản đồ và lựa chọn độ khó | Website; `world_select.gdc`, `ro_map.gdc` | 3 bản đồ tự xây | Vùng có bố cục, spawn, độ khó, phần thưởng khác nhau; mở khóa có lưu |
| MVP, đấu trường, cơ chế cảnh báo | Website; `mvp_raid.gdc`, `boss_brain.gdc`, `raid_alerts.gdc` | 1 boss tự xây | Boss có cơ chế riêng, cảnh báo đọc được, thắng/thua/phần thưởng đúng |
| Tháp nhiều tầng và build lưu | Website; `tower_run.gdc`, `tower_events.gdc`, `tower_traps.gdc` | Chưa có | Chuyển tầng, bẫy/sự kiện, tăng độ khó, build và kỷ lục bền vững |
| Trang bị, phẩm chất, bộ đồ, ô thẻ | `equipment.gdc`, `uniques.gdc`, nhãn trang bị | Chưa có | Kho/mặc/tháo/thuộc tính thực sự tác động trận, không nhân đôi vật phẩm |
| Rèn, nâng phẩm chất, chế tạo | Nhãn forge/refine/socket trong locale | Chưa có | Giá/nguyên liệu/giới hạn được kiểm tra, thao tác thất bại không trừ tài nguyên |
| Album thẻ, ghép và thẻ vĩnh viễn | `card_fusion.gdc`, `card_fusion_all.gdc`, nhãn album | Chưa có | Thu thập, số bản sao, trang bị và ghép có hiệu lực, tránh nhận thưởng lặp |
| Kho Kafra, đồ khởi đầu, túi đồ | Nhãn storage/inventory/starting gear | Chưa có | Dung lượng, chuyển vật phẩm, bộ khởi đầu và save có kiểm tra dữ liệu |
| Pet, homunculus, triệu hồi | `homunculus.gdc`, `summons.gdc`, `doram.gdc`; nhãn pet | Chưa có | Đồng hành có hành vi, quyền sở hữu, phát triển và vai trò phân biệt |
| Nhiệm vụ và sự kiện | `quest_run.gdc`, `festival_run.gdc`, `morroc_event.gdc` | Chưa có | Mục tiêu/tiến độ/hoàn thành/thất bại/phần thưởng và nhận một lần |
| Thành tựu, danh hiệu, bộ sưu tập | `achievements.gdc`, `titles.gdc`, `legends.gdc` | Thống kê cơ bản | Điều kiện tiến độ, nhận thưởng, danh hiệu lựa chọn và lưu đúng |
| Tái sinh, Valhalla, Karma | `valhalla.gdc`, `karma.gdc`, `rebirth_marks.gdc` | Chưa có | Yêu cầu tái sinh, phần mất/giữ, lợi ích lâu dài và chống nhận lại |
| Bàn thờ, lựa chọn rủi ro | `altars.gdc` | Chưa có | Giao kèo có lợi/hại và tác động kiểm chứng được |
| Thành phố và NPC | `town.gdc`, `town_crowd.gdc`, nhiều cửa sổ dịch vụ | Menu chuẩn bị | Thành phố offline với NPC, dịch vụ và hoạt động có trạng thái |
| Đồng đội thay co-op online | `bot.gdc`, `net_sync.gdc`; website nói tối đa 4 người | Chưa có | Tổ đội người chơi + AI, vai trò, bám đội, né và cứu/hỗ trợ; không đòi server |
| Chat, trao đổi, xã hội offline | `chat_log.gdc`, `trade.gdc`, `channel_bot.gdc` | Chưa có | NPC/AI và thương nhân cục bộ thay người chơi thật; không giả vờ có giao dịch online |
| AI chiến thuật bổ sung | Yêu cầu mới của người dùng | Chưa có | Theo/kết hợp kỹ năng/ưu tiên mục tiêu/chế độ chiến thuật có hiệu lực |
| Chat AI bổ sung | Yêu cầu mới của người dùng | Chưa có | Nêu rõ chatbot kịch bản hay mô hình ngôn ngữ; offline thật không gọi API |
| Điều khiển và trợ năng | `gamepad.gdc`, `mouse_walk.gdc`, `pad_hints.gdc` | Bàn phím + cần cảm ứng | Kiểm thử PC, cảm ứng, tạm dừng khi mất focus; gamepad nếu công bố hỗ trợ |
| Lưu lượt và tiến trình | `save.gdc`, `run_save.gdc`, `cloud_save.gdc` | Vàng/rèn luyện/thống kê + xuất/nhập | Schema/migration, đóng/mở lại, sao lưu/khôi phục; nói rõ có tiếp tục trận hay không |
| Âm thanh, hình ảnh và hiệu năng | `vfx.gdc`, `weather.gdc`, tài nguyên PCK | Hình pixel tự vẽ + âm tổng hợp | Kiểm tra trực quan, chữ Việt, tràn UI, horde đông, giới hạn bộ nhớ trên thiết bị thật |
| Web, PC, Android | Client gốc phát hành nhiều nền tảng | ZIP HTML/JS | Mỗi nền tảng có artifact chạy được và test thực tế; wrapper chưa build không được ghi hoàn tất |

## Quy tắc chuyển offline

Không thể giữ nguyên ý nghĩa các tính năng nhiều người trong một game hoàn toàn offline. Co-op đổi thành đồng đội AI; thành phố đông người đổi thành NPC/đám đông giả lập; trao đổi đổi thành kinh tế cục bộ; bảng xếp hạng đổi thành kỷ lục trên máy. Tài khoản, chat người thật, cloud save và cập nhật tự động không phải điều kiện để chơi. Nếu thêm dịch vụ mạng tùy chọn, phải tách rõ khỏi chế độ offline.

Chat AI sinh văn bản hoàn toàn offline cần mô hình và runtime cục bộ, có giới hạn RAM/dung lượng/tốc độ theo PC hoặc Android. Chat theo luật có thể hoạt động ngay với gói nhỏ nhưng không tương đương mô hình ngôn ngữ. Không dùng nhãn “AI đầy đủ như dự án tham khảo” trước khi xác nhận cơ chế và kiểm thử.

## Khảo sát khả năng khôi phục client

Đã đọc header của 131 tệp `.gdc`: tất cả có magic `GDSC`, bytecode version `101`. Thân `game_data.gdc` có dấu hiệu nén Zstandard. [Bảng phiên bản GDRE](https://github.com/GDRETools/gdsdecomp/blob/master/bytecode/bytecode_versions.cpp) có revision ổn định cho bytecode 101; đây là căn cứ để thử phục hồi, chưa bảo đảm tất cả scene, tài nguyên và extension của Godot 4.7.2 sẽ hoạt động.

[GDRE Tools](https://github.com/GDRETools/gdsdecomp) cung cấp khôi phục script/project/tài nguyên và CLI headless. GDExtension là thành phần không được giải biên dịch thành mã nguồn bởi công cụ này. Mọi thử nghiệm khôi phục phải giữ tại `work/`, loại bỏ nội dung credentials khỏi khảo sát và không đưa mã/tài nguyên phục hồi vào GitHub.

### Kết quả thử khôi phục ngày 15/11/2026

GDRE Tools **2.7.4** từ release chính thức đã khôi phục vào `work/recovered/`, trả mã thoát `0`: **131/131 script**, **6.249/6.249 tài nguyên import** chuyển đổi thành công, **0 chuyển đổi thất bại**, **595 trường hợp lossy**. Có `project.godot`, các script `.gd` và scene văn bản. Dữ liệu lossy phản ánh giới hạn từ bản tài nguyên đã nén; không đồng nghĩa với khôi phục nguồn tác giả nguyên vẹn. `eos/credentials.cfg` được loại khỏi quá trình trích xuất.

Đếm khóa cấp ngoài cùng trong các dictionary của `game_data.gd` phục hồi được:

| Dictionary | Số mục |
| --- | ---: |
| Nghề gốc | 11 |
| Bản đồ | 20 |
| Vùng | 11 |
| Kỹ năng | 349 |
| Thẻ | 163 |
| Vật phẩm | 209 |
| Pet | 46 |
| Nhiệm vụ | 20 |
| Thành tựu | 73 |
| Nâng cấp | 24 |

Đây là số bản ghi tĩnh của mẫu **0.1.273**, không phải bằng chứng mọi mục đã được thử trong game. Kỹ năng có thể bao gồm biến thể, tiến hóa hoặc mục hỗ trợ; vật phẩm có thể gồm nhiều loại; không dùng các con số để khẳng định số nội dung gameplay độc lập.

Luồng bắt đầu gốc có tính cục bộ: nút vào game trong hai kiểu màn hình đăng nhập gọi trực tiếp màn hình chọn nhân vật, rồi chọn vùng/chuẩn bị. Save cục bộ tồn tại riêng; cloud save là thành phần bổ sung. Cũng có điều khiển bot và tham số dòng lệnh chọn đồng đội. Điều đó mở ra hướng bảo tồn nhiều tính năng gốc khi chuyển offline, nhưng chưa thay thế bước kiểm tra chạy, tắt các thành phần tự kết nối và kiểm thử export web/PC/Android.

## Điều kiện gọi là hoàn thiện

Chỉ gọi một nền tảng hoàn thiện khi tính năng trong danh sách đã có đường thao tác thật, bộ test phù hợp đạt, kiểm thử hiển thị/điều khiển đạt và artifact khởi động được trên nền tảng đó. Số lượng mục dữ liệu tự tạo hoặc nút menu không thay thế việc kiểm tra hành vi; một gói wrapper hoặc một test DOM giả lập cũng không chứng minh APK/EXE hoạt động.
