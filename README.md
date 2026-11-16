# RAG-SVV — các dự án Ragnarok và game sinh tồn tiếng Việt

Hướng hiện tại là **chuyển client Midgard Survivors gốc sang offline, giữ sprite Ragnarok, bản đồ và gameplay gốc**, thêm tiếng Việt và đồng đội AI. Project khôi phục và các bản game chỉ nằm cục bộ trong `midgard-offline/work/`; repo công khai chứa công cụ và phần bổ sung tự viết. Xem [client gốc offline](midgard-offline/docs/ORIGINAL_CLIENT.md).

**Phát triển từ web, không cần Codex desktop:** [ChatGPT web + GitHub Actions](midgard-offline/docs/WEB_GITHUB_DEVELOPMENT.md). Workflow tự lấy bản nền từ nguồn chính thức và tái dựng project trên runner; không phụ thuộc ổ E: hay máy ban đầu.

| Hướng | Mục tiêu | Tài liệu | Trạng thái |
| --- | --- | --- | --- |
| Client Midgard gốc offline | Giữ sprite Ragnarok, 11 nghề, bản đồ và các hệ thống từ client gốc; thêm AI và Việt hóa | [Client gốc](midgard-offline/docs/ORIGINAL_CLIENT.md) | Đã khôi phục và chạy thử cảnh thị trấn/chiến đấu; đang nghiệm thu và xuất các nền tảng |
| Prototype tự xây trước đây | Mẫu HTML/JS thử nghiệm các luật sinh tồn | [midgard-offline/](midgard-offline/) | Hướng phụ; hình tự vẽ không phải sprite Ragnarok, không phải bản bàn giao client gốc |
| Nintendo Switch | Việt hóa bản mod Vampire Survivors mang phong cách Ragnarok Online | [switch/](switch/) | Đã có công cụ và bản dịch thử nghiệm; chưa test Switch |
| Web / Server Việt Nam | Nghiên cứu Việt hóa [ro-survivors.com](https://ro-survivors.com/) và khả năng xây server được cấp phép | [web/](web/) | Chưa có mã nguồn/quyền chạy server |

**Lưu ý pháp lý và kỹ thuật:** `type0labs-dev/ragnarok-survivors` **không phải** mã nguồn của `ro-survivors.com`. Không được xem việc có repo Switch là quyền sao chép hoặc mở server trò chơi web. Việc đưa mã nguồn upstream vào dự án công khai cần có giấy phép phù hợp; tài nguyên game và khóa cá nhân không được đẩy lên GitHub.

## Prototype trước đây — không phải client Ragnarok gốc

Mở [midgard-offline/index.html](midgard-offline/index.html) bằng trình duyệt để chơi bản **Biên niên Midgard**. Game dùng HTML, CSS và JavaScript thuần; không cần tài khoản, máy chủ game, thư mục `E:\Game\RagnarokSVV` hay kết nối Internet khi chơi. Mã, hình vẽ và luật chơi của bản thử nghiệm được xây riêng trong repo.

Prototype này độc lập với project Godot khôi phục. Không dùng việc build được prototype để kết luận client gốc đã hoàn thiện. Đọc [hướng dẫn prototype](midgard-offline/README.md), [kiểm kê](midgard-offline/docs/client-analysis.md) và [bảng đối chiếu tính năng](midgard-offline/docs/FEATURE_PARITY.md).

Có thể tiếp tục phát triển repo trên máy khác hoặc môi trường cloud với Node.js 20 trở lên. Bản build ZIP tự chứa mọi tệp chơi offline; dữ liệu lưu giữa các thiết bị được chuyển bằng **Xuất lưu / Nhập lưu**.

## Hướng Nintendo Switch — tài liệu triển khai

Phần này làm bản vá tiếng Việt cho **Ragnarok Survivors**, bản mod Nintendo Switch biến **Vampire Survivors** thành phong cách Ragnarok Online.

> **Trạng thái:** Bộ công cụ Việt hóa thử nghiệm. Chưa có bản game Việt hóa hoàn chỉnh / NSP / bản build đã kiểm thử.

## Mã nguồn gốc

- Upstream: https://github.com/type0labs-dev/ragnarok-survivors
- Mã nguồn gốc là bộ **công cụ dựng mod trên Nintendo Switch**, **không phải phần mềm server Ragnarok Online**.
- Repo này chứa **công cụ và bản dịch do cộng đồng viết riêng**, không sao chép mã nguồn chưa được cấp phép, game hay tài nguyên đồ họa/âm thanh của bên thứ ba.
- Hãy đọc README của upstream và tuân thủ giấy phép/điều kiện của từng thành phần.

## Cách thực hiện (Windows PowerShell)

Yêu cầu: Python 3.12+, git, bản Vampire Survivors Switch **1.15.113** hợp pháp và client Ragnarok Online cần thiết cho upstream. Dữ liệu game chỉ lưu ở máy của bạn.

```powershell
git clone https://github.com/type0labs-dev/ragnarok-survivors.git
git clone https://github.com/ronvotri/rag-svv.git
cd ragnarok-survivors
py -m pip install -r requirements.txt
# Chuẩn bị thư mục ROMFS Vampire Survivors 1.15.113 và client Ragnarok Online theo README gốc.
py tools/build.py --romfs "D:\\VS-ROMFS" --ro "D:\\RO-client" --sd "D:\\RAG-output"
cd ../rag-svv
py tools/apply_vi.py --upstream "../ragnarok-survivors" --data "D:\\RAG-output\\atmosphere\\contents\\010089A0197E4000\\romfs\\Data\\data.unity3d"
```

Công cụ `apply_vi.py` chỉ sửa **bảng ngôn ngữ I2** trong tệp mod đã build. Nó ghi bản dịch tiếng Việt trong `locales/vi-VN.json` vào vị trí ngôn ngữ **Português (Brasil)** (slot 5) để thử nghiệm, và tự tạo bản sao `.bak` trước khi thay thế. Do đó phải chọn tiếng Bồ Đào Nha (Brazil) trong cài đặt ngôn ngữ của game để thấy bản dịch thử nghiệm. Chạy công cụ **sau mỗi lần build**.

`--dry-run` cho phép kiểm tra số khóa khớp mà không chỉnh sửa file:

```powershell
py tools/apply_vi.py --upstream "../ragnarok-survivors" --data "D:\\RAG-output\\atmosphere\\contents\\010089A0197E4000\\romfs\\Data\\data.unity3d" --dry-run
```

## Tham khảo bản Việt hóa Vampire Survivors Switch 1.16.100

Đã kiểm tra bản vá do người dùng cung cấp (tên archive ghi `juskiddin & Chum`, màn hình ghi công `Bánh Cuốn & Chum`):
- Chỉ có file `010089a0197e4000/romfs/Data/data.unity3d`.
- Trong metadata, game gốc là **1.16.100**, không khớp phiên bản **1.15.113** mà Ragnarok Survivors yêu cầu.
- Bảng I2Languages có **6.893** khóa, mỗi khóa 14 ngôn ngữ. Slot 0 (English) chứa **5.951** chuỗi khác rỗng; trong đó nhóm `lang/` có 913 khóa, 909 có nội dung.
- Không chép đè `data.unity3d` của 1.16 lên mod 1.15.113. Chỉ dùng nội dung văn bản làm tham khảo, ghép theo khóa I2, rồi test font.
- **Không** push bản dịch của bên thứ ba lên repo công khai nếu chưa được phép.

Sau khi giải nén bản vá tham khảo trên máy tính, chạy:

```powershell
# Chạy trong thư mục rag-svv. Đã clone repo upstream và cài requirements ở phần trên.
py tools/extract_reference_vi.py --upstream "../ragnarok-survivors" --data "D:\\VS-VI-1.16\\010089a0197e4000\\romfs\\Data\\data.unity3d"
py tools/prepare_vi.py --source "work/source-vi.private.json" --mode ui
# Sau khi build Ragnarok bằng tools/build.py:
py tools/apply_vi.py --upstream "../ragnarok-survivors" --data "D:\\RAG-output\\atmosphere\\contents\\010089A0197E4000\\romfs\\Data\\data.unity3d" --translations "work/vi-merged.private.json" --dry-run
# Bỏ --dry-run sau khi đã đối chiếu tỷ lệ khóa hợp lệ để thực sự tạo bản vá.
```

`--mode ui` chỉ nhập văn bản giao diện dùng chung, sau đó ưu tiên bản dịch trong `locales/vi-VN.json`. `--mode all` nhập thêm mô tả/nhiệm vụ/nhân vật từ Vampire Survivors nhưng **chưa được rà soát** để khớp Ragnarok, không nên dùng cho bản phát hành. Bản thử nghiệm ghi vào vị trí ngôn ngữ PT-BR (slot 5), còn văn bản tham khảo 1.16 nằm ở EN (slot 0). Phần font và kiểm thử trên Switch vẫn chưa hoàn tất.

## Phạm vi và việc cần làm

1. Dịch tên kỹ năng, nhân vật, vật phẩm; sau đó dịch mô tả, bestiary, thành tựu, menu.
2. Giữ nguyên mã khóa I2, ký hiệu điều khiển, thông số và placeholder; ưu tiên thuật ngữ quen thuộc với game thủ Ragnarok Việt Nam.
3. Xác minh font **ă â ê ô ơ ư đ** cùng dấu thanh: font gốc chưa được xác nhận hỗ trợ đầy đủ tiếng Việt.
4. Test kỹ giao diện không tràn chữ, bản vá khởi động được và không đổi gameplay.
5. Chỉ chia sẻ bản vá/công cụ; **không** đưa ROMFS, NSP chứa game, `data.grf`, `prod.keys` hoặc nội dung có bản quyền lên GitHub.

**Lưu ý:** Việc tạo file và công cụ chưa chứng minh game chạy được. Cần có bản dump hợp pháp và thiết bị Switch để build/test thực tế.

## Ghi công

- Dự án tham khảo: [type0labs-dev/ragnarok-survivors](https://github.com/type0labs-dev/ragnarok-survivors)
- Vampire Survivors © poncle; Ragnarok Online © Gravity Co., Ltd.
- Bản Việt hóa cộng đồng không liên kết chính thức với các chủ sở hữu kể trên.
