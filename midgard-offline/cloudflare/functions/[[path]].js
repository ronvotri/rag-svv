/** Same-origin delivery for the large original Godot Web files.
 * Pages static assets are handled by the CDN and never call this function.
 * The R2 bucket is private. No gameplay or save data is sent to R2.
 */
export async function onRequest(context) {
  const { request, env } = context;
  if (request.method !== "GET" && request.method !== "HEAD") {
    return new Response("Method not allowed", { status: 405, headers: { Allow: "GET, HEAD" } });
  }
  const filename = new URL(request.url).pathname.slice(1);
  const allowed = new Set((env.LARGE_ASSETS || "").split(",").filter(Boolean));
  if (!/^[A-Za-z0-9_.-]+$/.test(filename) || !allowed.has(filename)) {
    return new Response("Not found", { status: 404 });
  }
  if (!env.GAME_ASSETS || !/^[a-f0-9]{7,64}$/.test(env.ASSET_VERSION || "")) {
    return new Response("Game storage is not configured", { status: 503 });
  }
  const key = `releases/${env.ASSET_VERSION}/${filename}`;
  const rangeRequest = request.headers.has("Range");
  const object = await env.GAME_ASSETS.get(
    key,
    rangeRequest ? { range: request.headers } : {}
  );
  if (!object) return new Response("Not found", { status: 404 });
  const headers = new Headers();
  object.writeHttpMetadata(headers);
  headers.set(
    "Content-Type",
    filename.endsWith(".wasm") ? "application/wasm" :
    filename.endsWith(".pck") ? "application/octet-stream" : "application/octet-stream"
  );
  headers.set("Cache-Control", "public, max-age=31536000, immutable");
  headers.set("Accept-Ranges", "bytes");
  if (object.httpEtag) headers.set("ETag", object.httpEtag);
  let status = 200;
  if (rangeRequest && object.range) {
    const first = object.range.offset;
    const last = first + object.range.length - 1;
    headers.set("Content-Range", `bytes ${first}-${last}/${object.size}`);
    headers.set("Content-Length", String(object.range.length));
    status = 206;
  } else {
    headers.set("Content-Length", String(object.size));
  }
  return new Response(request.method === "HEAD" ? null : object.body, { status, headers });
}
