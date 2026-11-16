# Build web, Windows và Android

**Phân biệt hai nhánh kỹ thuật:** các lệnh `build*.mjs` bên dưới đóng gói prototype JavaScript độc lập 0.2. Các bản giữ sprite, bản đồ và gameplay Ragnarok gốc phải xuất từ project Godot riêng trong `work/recovered-offline/`; không được lấy thành công của prototype làm bằng chứng bản gốc đã hoàn tất. Tài nguyên và mã phục hồi chỉ nằm trong `work/`, bị Git bỏ qua.

Cả ba nền tảng dùng cùng các tệp game trong `midgard-offline/`. Các wrapper dưới đây không chuyển đổi engine của client gốc và không tự bổ sung tính năng gameplay còn thiếu. Không đưa EXE/PCK, tài nguyên trích từ client hoặc thông tin tài khoản vào bản build.

## Trạng thái

| Nền tảng | Gói tạo được | Giới hạn kiểm chứng |
| --- | --- | --- |
| Web | ZIP mở trực tiếp `index.html` | Tests Node/DOM giả lập; cần QA hình ảnh trên browser thật |
| Windows x64 | Thư mục portable có `MidgardOffline.exe`, Chromium/Electron đi kèm | Build chưa ký mã, chưa QA hiển thị hoặc chơi đầy đủ |
| Android 8+ | APK native WebView, app ID `com.votrivalley.midgardoffline` | Chỉ bản **DEBUG-TEST**, chưa test thiết bị; chưa đăng ký khóa ký phát hành lâu dài |

Đóng gói thành công không có nghĩa là đã đạt full tính năng hay đã được nghiệm thu trên thiết bị. Xem bảng đối chiếu tính năng riêng trong tài liệu dự án.

## Web

Node.js >=20, không cài npm dependencies:

```powershell
node midgard-offline/tools/build.mjs
```

Version lấy từ `midgard-offline/package.json`. Đầu ra: `midgard-offline/dist/midgard-offline-<version>.zip` và `SHA256SUMS.txt`. Bộ đóng gói chỉ lấy các tệp web ở thư mục game và tài nguyên trong `assets/`; không đọc `work/`, `platforms/`, `reference/`, `private/` hoặc client gốc.

## Windows

Chuẩn bị bản phân phối Windows x64 của Electron chính thức; đặt đường dẫn đến thư mục chứa `electron.exe` bằng biến `MIDGARD_ELECTRON_DIR` hoặc tham số:

```powershell
node midgard-offline/tools/build-desktop.mjs --electron-dir "C:\toolchains\electron-win32-x64" --zip
```

Không cần Electron trên máy người chơi: Chromium và DLL đã nằm trong thư mục portable. Mở `MidgardOffline.exe` và giữ các tệp cạnh nó. `--zip` dùng `tar` của hệ điều hành để đóng gói; bỏ tham số này vẫn tạo thư mục chạy được. Không ghi đường dẫn toolchain riêng của người phát triển vào source.

Wrapper bật sandbox, context isolation, tắt Node integration trong trang game, chặn quyền trình duyệt, cửa sổ mới và yêu cầu mạng bên ngoài. Nội dung cục bộ được phục vụ qua scheme `midgard://game/`. Save ở thư mục dữ liệu ứng dụng của tài khoản Windows, không nằm cạnh EXE; đổi thư mục portable không đổi vị trí save. Save của browser và save của app Windows độc lập; dùng Xuất/Nhập lưu để chuyển.

Electron là thành phần bên thứ ba theo giấy phép đi kèm. Giữ `LICENSE` và `LICENSES.chromium.html` trong bản phân phối. Lần kiểm tra toolchain cục bộ sử dụng Electron 38.8.6 đã có trên máy; trước bản phát hành chính thức cần cập nhật runtime được hỗ trợ và kiểm tra lại.

## Android

Builder sử dụng **JDK 17+**, **Android SDK platform 36**, **build-tools 36.0.0**. Không dùng Gradle và không tải package trong quá trình build. Cài toolchain chính thức riêng; có thể dùng lại toolchain đã có trên máy mà không sửa dự án khác.

```powershell
node midgard-offline/tools/build-android.mjs --java-home "C:\toolchains\jdk-21" --android-sdk "C:\toolchains\android-sdk"
```

Cũng có thể cung cấp `JAVA_HOME`, `ANDROID_SDK_ROOT`. Android versionCode mặc định `200`; tăng bằng `--version-code` khi cần. APK nằm tại `midgard-offline/dist/android/MidgardOffline-<version>-Android-DEBUG-TEST.apk`.

Builder biên dịch Java, dex, resources, zipalign rồi ký và chạy `apksigner verify`. App không xin quyền Internet hoặc truy cập toàn bộ bộ nhớ. WebView đọc các asset đóng gói qua origin cục bộ được chặn trong `shouldInterceptRequest`, không tải trang online. Xuất/Nhập save dùng trình chọn tài liệu của Android, không cần quyền bộ nhớ rộng. Nút Quay lại tạm dừng; nhấn lại lần hai để thoát.

Khóa debug riêng được tạo lần đầu và giữ ở `midgard-offline/work/android-debug/`, bị Git bỏ qua. Khóa này **không dùng để phát hành ổn định**, không phải khóa PKM Chuyển Sinh và không được đưa vào APK/ZIP/source. Không gỡ ứng dụng hoặc xóa dữ liệu khi nâng bản; hãy xuất save trước mọi thử nghiệm cài đặt. Trước khi gửi cho người chơi cần thống nhất khóa release lâu dài, sao lưu khóa ngoài repo, tăng versionCode cho mỗi bản cập nhật và xác minh cùng chứng thư. Không tự tái sử dụng danh tính ký của dự án PKM.

Trên Windows, một số công cụ Android không đọc được đường dẫn Unicode. Builder tự tạo thư mục staging trong temp, sau đó sao chép APK hoàn thiện về `dist/`.

## QA trước khi gọi là bản hoàn thiện

- Web: mở khi tắt mạng; kiểm tra layout, âm thanh, chuột/phím/cảm ứng, xuất/nhập và tải lại save.
- PC: chạy EXE từ thư mục giải nén mới, kiểm tra save khi nâng bản, khi mất focus và độ phân giải khác nhau.
- Android: kiểm tra trên thiết bị thật WebView hiện hành, cảm ứng nhiều ngón, xoay/mất focus, back, xuất/nhập save, hiệu năng/độ nóng trong trận dài.
- Đối chiếu nội dung và chức năng với bản gốc riêng. Wrapper không chứng minh độ tương đồng tính năng.

Tham khảo kỹ thuật: [Android in-app web content](https://developer.android.com/develop/ui/views/layout/webapps/load-local-content), [Electron security](https://www.electronjs.org/docs/latest/tutorial/security).

## Xuất Android từ project Godot gốc đã chuẩn bị riêng

Đây là tuyến client native giữ dữ liệu và sprite gốc, tách với wrapper WebView của prototype. Cần project private đã được vá offline, Việt hóa và kiểm tra lỗi script/import bằng đúng Godot 4.7.2 trước khi xuất. Bộ template chính thức phải có `android_debug.apk`; Java/Android SDK dùng cùng yêu cầu ở trên.

```powershell
python midgard-offline/tools/create-original-android-preset.py midgard-offline/work/recovered-offline --templates midgard-offline/work/tools/export-templates-4.7.2 --debug-keystore midgard-offline/work/android-debug/midgard-debug.keystore

python midgard-offline/tools/export-original-android.py --godot midgard-offline/work/tools/godot-4.7.2/Godot_v4.7.2-stable_win64_console.exe --project midgard-offline/work/recovered-offline --java-home "C:\toolchains\jdk-21" --android-sdk "C:\toolchains\android-sdk" --debug-keystore midgard-offline/work/android-debug/midgard-debug.keystore
```

Chạy lệnh tạo preset một lần; nếu đã tồn tại, công cụ dừng để tránh ghi đè cấu hình đã rà soát. Export helper sử dụng EditorSettings portable cạnh editor (`_sc_`, `editor_data/`), staging ASCII cho công cụ ký và biến môi trường debug-keystore chính thức của Godot. Không sửa cấu hình hoặc khóa của PKM Chuyển Sinh. Sau export, công cụ xác minh chữ ký rồi chép về `work/original-builds/android/MidgardSVVOffline-DEBUG-TEST.apk`, kèm hash SHA-256 và `android-export.log`.

App ID riêng của tuyến Godot là `com.votrivalley.midgardsvvoffline`, khác prototype và bản chính thức. Preset chỉ arm64, minSDK26, targetSDK36; tắt Internet và quyền bộ nhớ rộng. Đây vẫn là khóa debug cục bộ, chưa phải bản cập nhật đã ký bằng danh tính release lâu dài. Không đưa APK/PCK hoặc project phục hồi lên repo công khai. Thành công của lệnh export chưa chứng minh UI cảm ứng, save, hiệu năng hoặc mọi hệ thống gốc chạy đúng; cần QA bản native riêng.

Hội thoại LLM bằng JavaScript trong browser không tự chạy trong client Godot native. Hỗ trợ LLM native, phần hướng dẫn theo luật và đồng đội AI phải được kiểm chứng riêng, không suy ra từ việc đóng gói APK.
