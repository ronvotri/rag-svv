'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const worker = fs.readFileSync(
  path.resolve(__dirname, '../cloudflare/godot-split-sw.js'), 'utf8'
);

async function simulate(assetBytes, assetParts, extra = {}) {
  const handlers = {};
  const base = 'https://ragnarok.example/';
  const files = {};
  assetParts.forEach((bytes, i) => {
    files[`parts/abcdef0/index.wasm/${String(i).padStart(4,'0')}.bin`] = bytes;
  });
  const manifest = {
    schema: 1, version: 'abcdef0',
    large_assets: {
      'index.wasm': {
        name: 'index.wasm',
        size: assetBytes.length,
        type: 'application/wasm',
        parts: assetParts.map((part, i) => ({
          path: `parts/abcdef0/index.wasm/${String(i).padStart(4,'0')}.bin`,
          size: part.length
        }))
      }
    }
  };
  const fetches = [];
  const networkFetch = async req => {
    const url = new URL(typeof req === 'string' ? req : req.href ?? req.url);
    fetches.push(url.pathname);
    const relative = url.pathname.slice(1);
    if (relative === 'asset-map.json') return Response.json(manifest);
    if (Object.hasOwn(files, relative)) return new Response(files[relative]);
    return new Response('Not found', { status: 404 });
  };
  const self = {
    registration: { scope: base },
    addEventListener(type, cb) { handlers[type] = cb; },
    skipWaiting: async () => {},
    clients: { claim: async () => {} }
  };
  vm.runInNewContext(worker, {
    self,
    fetch: networkFetch,
    URL, Response, Headers, ReadableStream, Uint8Array, AbortController,
    console
  });
  async function request(resource, headers = {}) {
    let promise;
    handlers.fetch({
      request: new Request(base + resource, { headers }),
      respondWith(value) { promise = value; }
    });
    if (!promise) return null;
    return await promise;
  }
  return { manifest, files, request, fetches, ...extra };
}

test('original wasm bytes are streamed in the exact order from Pages parts', async () => {
  const expected = Uint8Array.from({ length: 101 }, (_, i) => i);
  const chunks = [expected.slice(0, 16), expected.slice(16, 44), expected.slice(44)];
  const app = await simulate(expected, chunks);
  const response = await app.request('index.wasm');
  assert.equal(response.status, 200);
  assert.equal(response.headers.get('content-type'), 'application/wasm');
  assert.equal(Number(response.headers.get('content-length')), expected.length);
  assert.deepEqual(Buffer.from(await response.arrayBuffer()), Buffer.from(expected));
  assert.equal(app.fetches.filter(x => x.includes('/parts/')).length, 3);
});

test('byte ranges do not silently corrupt resumed downloads', async () => {
  const expected = Uint8Array.from({ length: 50 }, (_, i) => 255 - i);
  const app = await simulate(expected, [expected.slice(0, 12), expected.slice(12, 30), expected.slice(30)]);
  const range = await app.request('index.wasm', { Range: 'bytes=17-38' });
  assert.equal(range.status, 206);
  assert.equal(range.headers.get('content-range'), 'bytes 17-38/50');
  assert.deepEqual(Buffer.from(await range.arrayBuffer()), Buffer.from(expected.slice(17, 39)));
  const invalid = await app.request('index.wasm', { Range: 'bytes=99-' });
  assert.equal(invalid.status, 416);
});

test('missing parts reject the stream instead of yielding a partial game', async () => {
  const expected = Uint8Array.from({ length: 30 }, (_, i) => i);
  const app = await simulate(expected, [expected.slice(0, 10), expected.slice(10)]);
  delete app.files['parts/abcdef0/index.wasm/0001.bin'];
  const response = await app.request('index.wasm');
  await assert.rejects(response.arrayBuffer());
});

test('ordinary Godot JS is not replaced by the split loader', async () => {
  const bytes = new Uint8Array([1]);
  const app = await simulate(bytes, [bytes]);
  const response = await app.request('index.js');
  assert.equal(response.status, 404);
  assert.equal(app.fetches.filter(x => x.includes('/parts/')).length, 0);
});
