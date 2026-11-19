# Chat với mô hình ngôn ngữ chạy trên máy

Phần này tách khỏi hướng dẫn viên theo luật trong `ai.js`. `llm.js` là adapter cho **mô hình sinh văn bản thật**, chạy bằng Transformers.js và ONNX Runtime. Không dùng API chat hoặc máy chủ suy luận bên ngoài. Nội dung trả lời chỉ là văn bản; không có quyền sửa save, trao vật phẩm hoặc thực thi lệnh.

## Model và nguồn

- Model: [`onnx-community/Qwen2.5-0.5B-Instruct`](https://huggingface.co/onnx-community/Qwen2.5-0.5B-Instruct), ONNX conversion của Qwen2.5-0.5B-Instruct, giấy phép Apache-2.0.
- Revision bất biến: `516c8d04add8a80c5228f32102b57953b8d421a9`.
- Trọng số `onnx/model_quantized.onnx`: **512.096.557 byte**, SHA-256 `41834041ab1b29eff9fc592f1a29a1844133aea35832ea9fa91682be13016100`.
- Transformers.js **3.8.1**, từ gói npm chính thức `@huggingface/transformers`; runtime browser và ONNX WASM được chép vào cùng gói cục bộ. Hướng dẫn cấu hình: [Transformers.js env](https://huggingface.co/docs/transformers.js/v3.8.1/api/env).
- Giấy phép model từ repo [Qwen gốc](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct/blob/7ae557604adf67be50417f59c2c2f167def9a775/LICENSE), cùng giấy phép Transformers.js, ONNX Runtime và Jinja được đóng kèm.

Gói model/runtime hơn 530 MB, chưa tính bộ nhớ suy luận. Không commit model vào Git và không đưa vào bản ZIP nhỏ mặc định. Script chuẩn bị ghi vào `work/`, nơi Git đã bỏ qua.

## Chuẩn bị và kiểm thử

Từ thư mục repo, có Node.js và Internet ở bước tải ban đầu:

```text
node midgard-offline/tools/prepare-ai-model.mjs
node midgard-offline/tools/smoke-local-llm.mjs
node midgard-offline/tools/package-ai-model.mjs
```

Script đầu tải đúng revision model và xác minh dung lượng/SHA-256 trọng số. Runtime được cài riêng trong `midgard-offline/work/llm-runtime`, không thay package của game. Gói sẵn để dùng nằm ở `midgard-offline/work/local-ai/`; giữ nguyên cả cây thư mục và các giấy phép.

Script smoke thực hiện suy luận CPU thật trong Node, **chặn `fetch` trước khi nạp model**, rồi lưu kết quả/tốc độ đo được trong `work/local-ai-smoke.private.json`. Chỉ khi script thành công mới được nói đã kiểm thử suy luận Node. Unit test adapter và việc tải model xong không chứng minh suy luận thành công.

Kiểm thử tại máy hiện tại đã chạy thật: lượt đầu nạp khoảng 2,9 giây và sinh tối đa 64 token khoảng 42,8 giây; lượt có gợi ý luật game nạp khoảng 2,4 giây và sinh tối đa 48 token khoảng 7,6 giây. Hai kết quả đều có tiếng Việt nhưng câu trả lời đầu lạc ý, câu sau lặp lại câu hỏi; **chưa đạt chất lượng hướng dẫn gameplay để bật mặc định**. Đây là bằng chứng suy luận cục bộ, không phải nghiệm thu chất lượng trò chuyện. Tốc độ phụ thuộc máy, tải hệ thống và độ dài đầu ra.

Script package xác minh hash từng tài nguyên trong manifest rồi tạo `dist/midgard-local-ai-qwen-0.5b-q8-experimental.zip` và tệp SHA-256. Gói chỉ chứa model, runtime, giấy phép và adapter/tài liệu, không có client gốc, secret hoặc runtime Node. Giải nén cạnh HTML shell để có thư mục `local-ai/`; gói không tự thêm nút vào game hay tự kích hoạt model.

## Hợp đồng browser

Nạp `llm.js` như script thông thường, sau đó dùng `MidgardLLM.create({baseUrl:'./local-ai/'})`. Instance có `load(onProgress)`, `chat(text, context, history)`, `dispose()` và getter `status`.

- `load` đọc runtime/model cùng origin; tắt `allowRemoteModels`, bật `local_files_only` và dùng WASM một luồng mặc định.
- `chat` chỉ hoạt động khi model đã nạp; tối đa một lượt trả lời đồng thời. Context hỗ trợ `run`, `player`, `save`; history tối đa bốn tin gần nhất. Mỗi lượt sinh tối đa 96 token mặc định.
- Kết quả `{text,mode:'local-llm',model:'Qwen2.5-0.5B-Instruct'}` phải hiển thị như văn bản, không đưa thẳng vào HTML hoặc thực thi như lệnh.
- Phải có thao tác rõ ràng để nạp model lớn; không tự nạp khi mở menu. Khi không có model hoặc thiết bị không hỗ trợ, giữ hướng dẫn viên offline theo luật và báo đúng trạng thái.

ES module/WASM/model dùng tải tài nguyên cục bộ nên **không hỗ trợ mở thẳng qua `file://`**. Web cần localhost hoặc ứng dụng/PWA phục vụ tài nguyên cùng origin. CSP của shell phải cho phép tài nguyên cùng origin, `wasm-unsafe-eval` cho WASM và chính sách worker phù hợp runtime; không cần cho phép CDN hay origin ngoài.

## Giới hạn nền tảng

Module browser này chưa tự tích hợp vào game Godot native. Godot Web có thể gọi từ HTML shell qua JavaScriptBridge; PC/Android native cần một lớp WebView/bridge hoặc backend suy luận native riêng. Android WebView cần ánh xạ tài nguyên HTTPS cục bộ phù hợp và hỗ trợ tải file lớn; đường dẫn `file:///android_asset` không tự bảo đảm chạy model.

Suy luận Node CPU thành công không chứng minh browser WASM, WebGPU, Android hoặc thiết bị RAM thấp chạy ổn. Chưa thể gọi cả ba nền tảng đã hỗ trợ LLM chỉ vì cùng đọc được mã JavaScript. Mô hình 0,5B có chất lượng tiếng Việt và hiểu game hạn chế, có thể trả lời sai hoặc lặp; dữ liệu tình huống không biến nó thành nguồn xác thực cho luật game.
