/* Browser Service Worker for the ORIGINAL Godot Web export.
 * Only static Cloudflare Pages assets are used. No Pages Functions or R2.
 * The manifest is built with the original client on GitHub Actions.
 */
'use strict';

// Cache Storage is distinct from Godot save data (IndexedDB/localStorage).
// Cache only immutable, content-addressed asset chunks. Do not cache HTML,
// the runtime profile or any API response.
const PARTS_CACHE = 'svv-game-chunks-v1';
const MIN_FREE_AFTER_CHUNK = 64 * 1024 * 1024;
let cachePromise = null;
let cacheWritesDisabled = false;

const assetsURL = new URL('asset-map.json', self.registration.scope);
const manifestPromise = fetch(assetsURL.href, { cache: 'no-store' }).then(async response => {
  if (!response.ok) throw new Error('Missing game asset map: ' + response.status);
  const manifest = await response.json();
  if (manifest.schema !== 1 || !manifest.large_assets || !manifest.version) {
    throw new Error('Invalid game asset map');
  }
  return manifest;
});
const assetsPromise = manifestPromise.then(manifest => manifest.large_assets);

function openPartsCache() {
  if (!self.caches) return Promise.resolve(null); // WebView/test fallback.
  if (!cachePromise) {
    cachePromise = self.caches.open(PARTS_CACHE).catch(() => null);
  }
  return cachePromise;
}

async function allowWritingChunk(size) {
  if (cacheWritesDisabled) return false;
  try {
    const storage = self.navigator && self.navigator.storage;
    if (!storage || typeof storage.estimate !== 'function') return true;
    const estimate = await storage.estimate();
    if (Number.isFinite(estimate.quota) && Number.isFinite(estimate.usage) &&
        estimate.quota - estimate.usage < size + MIN_FREE_AFTER_CHUNK) {
      cacheWritesDisabled = true;
      return false;
    }
  } catch (_) {
    // Private browsers may not expose storage estimates. Cache API catches
    // quota errors independently and never blocks normal online play.
  }
  return true;
}

async function getPartResponse(url, part, signal, writeCache) {
  const cache = await openPartsCache();
  if (cache) {
    try {
      const hit = await cache.match(url.href);
      if (hit && hit.ok) {
        const length = hit.headers.get('content-length');
        if (!length || Number(length) === part.size) {
          return { response: hit, cacheWrite: null };
        }
        await cache.delete(url.href); // Reject a clearly mismatched old part.
      }
    } catch (_) { /* A failed local read is not a failed game load. */ }
  }
  const response = await fetch(url.href, { cache: 'default', signal });
  let cacheWrite = null;
  if (writeCache && cache && response.ok && response.status === 200 &&
      await allowWritingChunk(part.size)) {
    // Write the clone while the original Response is streamed to Godot.
    // At most one 16 MiB part is in flight; never buffer the full 700+ MiB PCK.
    cacheWrite = cache.put(url.href, response.clone()).catch(() => {
      cacheWritesDisabled = true; // Quota/privacy failure: continue online.
    });
  }
  return { response, cacheWrite };
}

self.addEventListener('install', event => {
  event.waitUntil(assetsPromise.then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    await self.clients.claim();
    const cache = await openPartsCache();
    if (!cache) return;
    try {
      const manifest = await manifestPromise;
      const current = new Set();
      for (const asset of Object.values(manifest.large_assets)) {
        for (const part of asset.parts || []) {
          current.add(new URL(part.path, self.registration.scope).href);
        }
      }
      // Delete only our obsolete binary parts. Never touch save data, other
      // caches or unchanged parts reused by the next published build.
      for (const request of await cache.keys()) {
        if (!current.has(request.url)) await cache.delete(request);
      }
    } catch (_) {
      // Cache maintenance is best effort; startup must never fail because of it.
    }
  })());
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

function createPartStream(asset, start, end, writeCache = true) {
  const parts = asset.parts;
  let partIndex = 0;
  let partStart = 0;
  let partReader = null;
  let currentPart = null;
  let bytesRead = 0;
  let delivered = 0;
  let abortController = null;
  let cacheWrite = null;
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
          const part = await getPartResponse(
            pathURL, currentPart, abortController.signal, writeCache
          );
          const response = part.response;
          cacheWrite = part.cacheWrite;
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
          if (cacheWrite) await cacheWrite;
          cacheWrite = null;
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
          // Complete the last part's disk write before closing the stream.
          // This makes the very next launch reuse this part with no network.
          if (cacheWrite) await cacheWrite;
          cacheWrite = null;
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
    // Range requests may cancel early; only persist complete asset downloads.
    const fullAsset = range.start === 0 && range.end === size - 1;
    return new Response(createPartStream(asset, range.start, range.end, fullAsset), {
      status: range.status, headers
    });
  })());
});
