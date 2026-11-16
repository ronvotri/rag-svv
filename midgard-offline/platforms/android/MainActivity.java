package com.votrivalley.midgardoffline;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;
import java.io.ByteArrayInputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.Collections;

public final class MainActivity extends Activity {
    private static final String ORIGIN = "https://appassets.androidplatform.net";
    private static final int IMPORT_SAVE = 101, EXPORT_SAVE = 102;
    private WebView web;
    private ValueCallback<Uri[]> fileCallback;
    private String pendingSave;
    private long lastBack;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        web = new WebView(this);
        setContentView(web);
        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(false);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(true);
        settings.setAllowFileAccessFromFileURLs(false);
        settings.setAllowUniversalAccessFromFileURLs(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setMediaPlaybackRequiresUserGesture(true);
        web.addJavascriptInterface(new SaveBridge(), "MidgardNative");
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return !isLocal(request.getUrl());
            }
            @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                if (!isLocal(uri)) return missing();
                String name = uri.getPath().substring("/assets/".length());
                if (name.contains("..") || name.contains("\\") || name.startsWith("/")) return missing();
                try {
                    return new WebResourceResponse(mime(name), "UTF-8", 200, "OK", Collections.singletonMap("Cache-Control", "no-cache"), getAssets().open(name));
                } catch (Exception error) { return missing(); }
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (fileCallback != null) fileCallback.onReceiveValue(null);
                fileCallback = callback;
                Intent pick = new Intent(Intent.ACTION_OPEN_DOCUMENT);
                pick.addCategory(Intent.CATEGORY_OPENABLE);
                pick.setType("application/json");
                try { startActivityForResult(pick, IMPORT_SAVE); }
                catch (Exception error) { fileCallback.onReceiveValue(null); fileCallback = null; }
                return true;
            }
        });
        web.loadUrl(ORIGIN + "/assets/index.html");
    }
    private static boolean isLocal(Uri uri) {
        return "https".equals(uri.getScheme()) && "appassets.androidplatform.net".equals(uri.getHost()) && uri.getPath() != null && uri.getPath().startsWith("/assets/");
    }
    private static String mime(String name) {
        if (name.endsWith(".html")) return "text/html";
        if (name.endsWith(".js")) return "application/javascript";
        if (name.endsWith(".css")) return "text/css";
        if (name.endsWith(".json")) return "application/json";
        if (name.endsWith(".svg")) return "image/svg+xml";
        if (name.endsWith(".png")) return "image/png";
        return "application/octet-stream";
    }
    private static WebResourceResponse missing() {
        return new WebResourceResponse("text/plain", "UTF-8", 404, "Not Found", Collections.emptyMap(), new ByteArrayInputStream(new byte[0]));
    }
    private final class SaveBridge {
        @JavascriptInterface public void exportSave(String json) {
            if (json == null || json.length() > 1000000) return;
            runOnUiThread(() -> {
                pendingSave = json;
                Intent save = new Intent(Intent.ACTION_CREATE_DOCUMENT);
                save.addCategory(Intent.CATEGORY_OPENABLE);
                save.setType("application/json");
                save.putExtra(Intent.EXTRA_TITLE, "midgard-save.json");
                try { startActivityForResult(save, EXPORT_SAVE); }
                catch (Exception error) { pendingSave = null; Toast.makeText(MainActivity.this, "Không mở được nơi lưu tệp.", Toast.LENGTH_LONG).show(); }
            });
        }
    }
    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request == IMPORT_SAVE && fileCallback != null) {
            fileCallback.onReceiveValue(result == RESULT_OK && data != null && data.getData() != null ? new Uri[]{data.getData()} : null);
            fileCallback = null;
        }
        if (request == EXPORT_SAVE) {
            if (result == RESULT_OK && data != null && data.getData() != null && pendingSave != null) {
                try (OutputStream output = getContentResolver().openOutputStream(data.getData(), "wt")) {
                    if (output == null) throw new IllegalStateException("No output stream");
                    output.write(pendingSave.getBytes(StandardCharsets.UTF_8));
                    Toast.makeText(this, "Đã xuất bản lưu.", Toast.LENGTH_SHORT).show();
                } catch (Exception error) { Toast.makeText(this, "Không thể ghi tệp lưu.", Toast.LENGTH_LONG).show(); }
            }
            pendingSave = null;
        }
    }
    @Override protected void onPause() {
        web.evaluateJavascript("window.dispatchEvent(new Event('blur'));", null);
        web.onPause();
        super.onPause();
    }
    @Override protected void onResume() { super.onResume(); if (web != null) web.onResume(); }
    @Override public void onBackPressed() {
        long now = System.currentTimeMillis();
        if (now - lastBack < 1800) { finish(); return; }
        lastBack = now;
        web.evaluateJavascript("window.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'}));", null);
        Toast.makeText(this, "Nhấn Quay lại lần nữa để thoát. Hãy xuất lưu trước khi gỡ ứng dụng.", Toast.LENGTH_SHORT).show();
    }
    @Override protected void onDestroy() {
        if (fileCallback != null) fileCallback.onReceiveValue(null);
        web.removeJavascriptInterface("MidgardNative");
        web.destroy();
        super.onDestroy();
    }
}
