/* Browser Service Worker for the ORIGINAL Godot Web export.
 * Only static Cloudflare Pages assets are used. No Pages Functions or R2.
 * The manifest is built with the original client on GitHub Actions.
 */
'use strict';

const assetsURL = new URL('asset-map.json', self.registration.scope);
const assetsPromise = fetch(assetsURL.href, { cache: 'no-store' }).then(async response => {
  if (!response.ok) throw new Error('Missing game asset map: ' + response.status);
  const manifest = await response.json();
  if (manifest.schema !== 1 || !manifest.large_assets) {
    throw new Error('Invalid game asset map');
  }
  return manifest.large_assets;
});

self.addEventListener('install', event => {
  event.waitUntil(assetsPromise.then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(self.clients.claim());
});

function parseRange(header, size) {
  if (!header) return { start: 0, end: size - 1, status: 200 };
  const match = /^bytes=(\d+)-(\d*)$/.exec(header.trim());
  if (!match) return null;
  const start = Number(match[1]);
  const end = match[2] ? Number(match[2]) : size - 1;
  if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end)
      || start < 0 || start >= size || end < start) return null;
  return { start, end: Math.min(end, size - 1), status: 206 };
}

function createPartStream(asset, start, end) {
  const parts = asset.parts;
  let partIndex = 0;
  let partStart = 0;
  let partReader = null;
  let currentPart = null;
  let bytesRead = 0;
  let delivered = 0;
  let abortController = null;
  const expected = end - start + 1;

  async function pump(controller) {
      try {
        if (delivered >= expected) {
          controller.close();
          return;
        }
        if (!partReader) {
          while (partIndex < parts.length && partStart + parts[partIndex].size <= start) {
            partStart += parts[partIndex].size;
            partIndex++;
          }
          if (partIndex >= parts.length) throw new Error('Incomplete split game asset');
          currentPart = parts[partIndex];
          bytesRead = 0;
          abortController = new AbortController();
          const pathURL = new URL(currentPart.path, self.registration.scope);
          // Content-addressed chunk URLs are immutable. Let the browser's
          // HTTP cache reuse downloads on reload where storage permits.
          const response = await fetch(pathURL.href, {
            cache: 'default',
            signal: abortController.signal
          });
          if (!response.ok || !response.body) {
            throw new Error('Missing game chunk: ' + currentPart.path + ' (' + response.status + ')');
          }
          partReader = response.body.getReader();
        }
        const result = await partReader.read();
        if (result.done) {
          if (bytesRead !== currentPart.size) {
            throw new Error('Truncated game chunk: ' + currentPart.path);
          }
          partReader.releaseLock();
          partReader = null;
          abortController = null;
          partStart += currentPart.size;
          partIndex++;
          return pump(controller);
        }
        const data = result.value;
        if (!(data instanceof Uint8Array)) throw new Error('Invalid game chunk bytes');
        const chunkStart = partStart + bytesRead;
        bytesRead += data.byteLength;
        if (bytesRead > currentPart.size) throw new Error('Oversized game chunk');
        const chunkEnd = chunkStart + data.byteLength - 1;
        const sliceStart = Math.max(start, chunkStart);
        const sliceEnd = Math.min(end, chunkEnd);
        if (sliceStart <= sliceEnd) {
          const cropped = data.subarray(sliceStart - chunkStart, sliceEnd - chunkStart + 1);
          delivered += cropped.byteLength;
          controller.enqueue(cropped);
        }
        if (delivered >= expected) {
          if (partReader) partReader.cancel().catch(() => {});
          if (abortController) abortController.abort();
          partReader = null;
          controller.close();
        }
      } catch (error) {
        if (partReader) partReader.cancel().catch(() => {});
        if (abortController) abortController.abort();
        controller.error(error);
      }
  }
  return new ReadableStream({
    pull: pump,
    cancel() {
      if (partReader) partReader.cancel().catch(() => {});
      if (abortController) abortController.abort();
    }
  });
}

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  const base = new URL(self.registration.scope);
  if (url.origin !== base.origin || !url.pathname.startsWith(base.pathname)) return;
  const filename = url.pathname.slice(base.pathname.length);
  if (!/^[A-Za-z0-9_.-]+$/.test(filename)) return;

  event.respondWith((async () => {
    const assets = await assetsPromise;
    const asset = assets[filename];
    if (!asset) return fetch(event.request);
    const size = Number(asset.size);
    if (!Number.isSafeInteger(size) || size <= 0 || !Array.isArray(asset.parts)
        || asset.parts.some(p => !Number.isSafeInteger(p.size) || p.size <= 0)
        || asset.parts.reduce((n, p) => n + p.size, 0) !== size) {
      return new Response('Invalid game asset manifest', { status: 502 });
    }
    const range = parseRange(event.request.headers.get('Range'), size);
    if (!range) {
      return new Response(null, {
        status: 416,
        headers: { 'Content-Range': 'bytes */' + size, 'Accept-Ranges': 'bytes' }
      });
    }
    const headers = new Headers({
      'Content-Type': asset.type || 'application/octet-stream',
      'Content-Length': String(range.end - range.start + 1),
      'Cache-Control': 'no-store',
      'Accept-Ranges': 'bytes'
    });
    if (range.status === 206) {
      headers.set('Content-Range', 'bytes ' + range.start + '-' + range.end + '/' + size);
    }
    return new Response(createPartStream(asset, range.start, range.end), {
      status: range.status, headers
    });
  })());
});
