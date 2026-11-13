# Ragnarok Survivors — Việt hóa (RAG-SVV)

Dự án cộng đồng làm bản vá tiếng Việt cho **Ragnarok Survivors**, bản mod Nintendo Switch biến **Vampire Survivors** thành phong cách Ragnarok Online.

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
