# Hành trình ngoại tuyến

`campaign.js` chứa hệ thống tiến trình viết mới cho game Midgard độc lập. Nội dung hiện có: **12 trang bị, 12 thẻ và 9 nhiệm vụ**. Các con số này là nội dung thực đã khai báo và có hiệu ứng; không đại diện số lượng nội dung trong game gốc.

## Lưu và phần thưởng

Profile có schema phiên bản 1 và được kiểm tra khi nhập. Module không tự ghi trình duyệt hay gọi mạng; giao diện chịu trách nhiệm lưu và xuất/nhập cùng bản lưu engine.

Vàng rèn luyện thuộc bản lưu engine. Hành trình dùng hai nguyên liệu riêng: **quặng** và **tinh chất**, nên không trả thêm một lần vàng từ cùng kết quả. Kết thúc lượt nhận quặng theo số quái và thời gian; chiến thắng có thưởng bổ sung, tinh chất và một thẻ. Lượt thất bại hạ ít nhất 40 quái cũng có một thẻ thường. Profile giữ ID của 4.096 lượt gần nhất để chống trả thưởng trùng trong phạm vi đó. Đây là cơ chế dữ liệu cục bộ, không phải chống gian lận máy chủ.

Tất cả giao dịch trả về profile mới và không sửa đối tượng cũ. Giao dịch thiếu nguyên liệu, chọn nội dung không có hoặc vượt bậc tối đa bị từ chối bằng lỗi tiếng Việt; giao diện cần hiển thị lỗi và giữ nguyên profile hiện tại.

## Trang bị và thẻ

Ba vị trí: vũ khí, giáp và bùa. Mỗi món chỉ sở hữu một bản và tinh luyện tối đa +10; chi phí tăng dần theo bậc. Chế tạo tiêu nguyên liệu và tạo món mới ở +0; trang bị món mới cùng vị trí thay món đang mặc. Hiệu ứng trang bị dùng chung cho mọi nghề trong bản hiện tại, chưa có yêu cầu cấp/nghề riêng.

Có thể gắn tối đa ba thẻ khác nhau đã sở hữu. Hợp nhất cần ba bản sao cùng loại: tiêu hai bản, giữ một bản và tăng một bậc, tối đa bậc 5. Hiệu ứng cộng vào máu, sát thương, tốc độ, hồi phục hoặc may mắn; bậc thẻ tăng hệ số hiệu ứng.

`bonuses(profile)` trả hiệu ứng cộng thêm: `hp` là số máu, `regen` là máu/giây, `power/speed/fortune` là tỉ lệ (0,08 tương ứng 8%). Engine cần áp dụng một lần khi tạo lượt để tránh cộng dồn sau mỗi lần mở menu.

## Nhiệm vụ, nghề và tái sinh

Nhiệm vụ dựa trên thống kê thật: số lượt, quái hạ gục, chiến thắng, thời gian, số món chế tạo, số lần tinh luyện, thủ lĩnh, tầng tháp và tái sinh. Phải hoàn thành rồi nhận thưởng bằng thao tác rõ ràng; mỗi nhiệm vụ chỉ nhận một lần trong profile.

Thống kê nghề tách riêng theo ID nghề. Danh hiệu lần lượt là Tập sự, Chuyển nghề (1 chiến thắng), Tinh anh (3) và Bậc thầy (10). Đây là danh hiệu tiến trình hiện tại, **không tự chứng minh đã có đầy đủ cây chuyển nghề/kỹ năng từ game gốc**.

Tái sinh cần tổng số chiến thắng đạt `3 × bậc tiếp theo` và tiêu `10 × bậc tiếp theo` tinh chất, tối đa 10 bậc. Mỗi bậc cộng 10 máu và 5% sát thương; giữ nguyên đồ, thẻ và thống kê. Không xóa save để mô phỏng một lần tái sinh.

Tháp chỉ cập nhật kỷ lục khi kết quả được ghi với `mode:'tower'` và `towerFloor` hợp lệ. Nhiệm vụ tầng tháp dựa vào kỷ lục đó. Việc module lưu kỷ lục không thay thế triển khai/quá trình kiểm thử gameplay Tháp trong engine.
