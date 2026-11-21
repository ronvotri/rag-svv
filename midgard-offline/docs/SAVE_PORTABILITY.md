# Save JSON và chuyển thiết bị

Bản này giữ định dạng profile mã hóa gốc. Nút **Sao lưu / Nạp save** mở được trên Web và Windows; cùng một JSON dùng để chuyển profile giữa hai nền tảng. Bạn bè, đội hình, vật phẩm, nhiệm vụ và các thiết lập bổ sung đều nằm trong profile và đi theo bản sao.

1. Về Prontera hoặc màn hình chính, bấm **Sao lưu / Nạp save**.
2. Chọn **Tải save về máy (JSON)**. Trên Windows, chọn vị trí lưu ngoài thư mục game; trên Web, kiểm tra file trong Downloads.
3. Chuyển JSON sang thiết bị mới rồi chọn **Nạp save từ máy (JSON)**. Bản `.svvsave` cũ vẫn được nhận.
4. Web chờ IndexedDB ghi xong rồi tải lại đúng trang hiện tại. Windows đóng game sau xác nhận; mở lại để dùng save đã nhập.

Trước khi thay profile, game kiểm tra checksum, thử giải mã bằng loader gốc, kiểm tra schema và giữ bản cũ tại `<tên-profile>.before-import.svvsave` trong `user://`. Nút **Khôi phục save trước lần nhập gần nhất** dùng bản này. Bản dự phòng cũ `svv-before-import.svvsave` vẫn được nhận trên profile offline thông thường. Profile QA dùng tên riêng và không thay bản dự phòng của người chơi.

File xuất là **tiến trình giữa các lượt**, không chuyển trận đang đánh. Cần về thành trước khi nhập. Khi thay profile, snapshot trận cũ trên thiết bị đích được bỏ để tránh tiếp tục một trận của nhân vật khác.

## Sửa lỗi trong đợt cập nhật 0.2.5

- Giao diện cũ gọi `get_vbox()` trên `AcceptDialog`, API không tồn tại trong Godot 4.7.2; nút mở save có thể báo lỗi trước khi hiện các thao tác. Nay tạo `VBoxContainer` thực và lồng hộp xác nhận vào đúng cửa sổ.
- Web từng tải lại ngay sau khi ghi bộ nhớ ảo, trước khi IndexedDB lưu xong. Nay chờ callback ghi bền vững, dừng autosave cũ trong lúc nhập và phục hồi profile cùng metadata Guardian nếu ghi thất bại.
- File có checksum đúng nhưng nội dung sai từng được nhận. Nay dùng staging để giải mã/kiểm tra trước khi thay save thật.
- Bản gốc 0.2.5 có bản cứu hộ localStorage theo số lần lưu. Khi nhập JSON, thay cả bản cứu hộ cùng giao dịch để nó không ghi đè save vừa nhập; lỗi ghi phục hồi cả hai.
- CSP của Web cho phép cơ chế JavaScriptBridge của Godot hoạt động. Kết nối mạng vẫn giới hạn cùng địa chỉ trang.
- Windows trước đây không có giao diện xuất/nhập; nay dùng hộp chọn file của hệ điều hành.

Save vẫn lưu trên thiết bị, không tự đồng bộ qua mạng. Giữ nguyên địa chỉ Web để tiếp tục dùng kho lưu của trình duyệt; đổi domain hoặc xóa dữ liệu trang cần nhập lại JSON. Cần tự giữ một bản JSON ngoài ứng dụng trước khi xóa cache, gỡ app hay chuyển máy.

## Kiểm chứng

- Test thực thi Godot 4.7.2 với project QA độc lập mở giao diện save, mở xác nhận, nhập profile mã hóa hợp lệ, từ chối file sai dù checksum đúng, kiểm tra bản cũ và rollback metadata Guardian.
- Test JavaScript mô phỏng IndexedDB trễ/lỗi quota/flush đang chạy để xác nhận không báo nhập xong trước callback.
- Đã kiểm tra schema và khóa định dạng của nguồn 0.2.5 tương thích profile cũ; không đưa khóa vào addon hoặc JSON xuất.
- Android có đường chọn tài liệu native, nhưng chưa nghiệm thu trên điện thoại thật. Chưa xác minh tải/nhập trên Safari/iOS hoặc kiểm thử chuyển file giữa hai thiết bị thật.

Chạy test runtime sau khi đã tải Godot bằng `SVV_GODOT=<đường-dẫn-binary> python -m unittest discover -s midgard-offline/tests -p test_original_save_runtime.py -v`. Test tự tạo user-data QA tạm dưới `work/`, không mở save đang chơi. Trên máy cục bộ có binary ghim trong `work/tools/`, test tự tìm binary đó.
