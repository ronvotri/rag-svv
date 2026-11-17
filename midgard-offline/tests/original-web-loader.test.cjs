'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const worker = fs.readFileSync(
  path.resolve(__dirname, '../cloudflare/godot-split-sw.js'), 'utf8'
);

async function simulate(assetBytes, assetParts, extra = {}) {
  const handlers = {};
  const base = 'https://ragnarok.example/';
  const files = {};
  const cacheMemory = extra.cacheMemory || new Map();
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
    caches: extra.enableCache ? {
      async open() {
        return {
          async match(uri) {
            const value = cacheMemory.get(uri);
            return value ? new Response(value) : undefined;
          },
          async put(uri, response) {
            if (extra.failCachePut) throw new Error('Simulated cache quota exhaustion');
            const bytes = await response.arrayBuffer();
            cacheMemory.set(uri, new Uint8Array(bytes));
          },
          async delete(uri) { return cacheMemory.delete(typeof uri === 'string' ? uri : uri.url); },
          async keys() { return [...cacheMemory.keys()].map(x => new Request(x)); }
        };
      }
    } : undefined,
    registration: { scope: base },
    addEventListener(type, cb) { handlers[type] = cb; },
    skipWaiting: async () => {},
    clients: { claim: async () => {} }
  };
  // Run with the actual Node Web Streams realm; vm cross-realm Response
  // streams can remain pending even though the worker byte logic is correct.
  new Function('self', 'fetch', worker)(self, networkFetch);
  async function request(resource, headers = {}) {
    let promise;
    handlers.fetch({
      request: new Request(base + resource, { headers }),
      respondWith(value) { promise = value; }
    });
    if (!promise) return null;
    const value = await Promise.race([promise, new Promise((_, reject) => setTimeout(() => reject(new Error('Service Worker request promise never settled')), 2500))]);
    return value;
  }
  return { manifest, files, request, fetches, cacheMemory, ...extra };
}

test('original wasm bytes are streamed in the exact order from Pages parts', async () => {
  const expected = Uint8Array.from({ length: 101 }, (_, i) => i);
  const chunks = [expected.slice(0, 16), expected.slice(16, 44), expected.slice(44)];
  const app = await simulate(expected, chunks);
  const response = await app.request('index.wasm');
  assert.equal(response.status, 200);
  assert.equal(response.headers.get('content-type'), 'application/wasm');
  assert.equal(Number(response.headers.get('content-length')), expected.length);
  const bytes = await Promise.race([response.arrayBuffer(), new Promise((_, reject) => setTimeout(() => reject(new Error('Service Worker response body never completed')), 2500))]);
  assert.deepEqual(Buffer.from(bytes), Buffer.from(expected));
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


test('shared or refreshed game.html is redirected to the bootstrap', () => {
  const vm = require('node:vm');
  const guard = fs.readFileSync(path.resolve(__dirname, '../cloudflare/game-entry-guard.js'), 'utf8');
  const run = (hasHandoff, controlled) => {
    const redirects = [];
    const store = new Map(hasHandoff ? [['svv-web-handoff', 'abcdef0']] : []);
    const context = {
      URL, location: {
        href: 'https://ragnarok.example/game.html',
        replace(url) { redirects.push(url.href); }
      },
      navigator: { serviceWorker: { controller: controlled ? {} : null } },
      sessionStorage: {
        getItem(key) { return store.get(key) ?? null; },
        removeItem(key) { store.delete(key); }
      }
    };
    vm.runInNewContext(guard, context);
    return { redirects, remaining: store.size };
  };
  assert.equal(run(false, true).redirects[0], 'https://ragnarok.example/?entry=game');
  assert.equal(run(true, false).redirects[0], 'https://ragnarok.example/?entry=game');
  const launched = run(true, true);
  assert.deepEqual(launched.redirects, []);
  assert.equal(launched.remaining, 0, 'handoff must be consumed on first launch');
});

test('mobile fullscreen requests landscape and supports manual rotation fallback', async () => {
  const vm = require('node:vm');
  const code = fs.readFileSync(path.resolve(__dirname, '../cloudflare/fullscreen-toggle.js'), 'utf8');
  const created = [];
  const calls = [];
  function element() {
    return {
      style: {}, handlers: {},
      setAttribute() {},
      addEventListener(name, handler) { this.handlers[name] = handler; }
    };
  }
  const doc = {
    readyState: 'complete', fullscreenElement: null, handlers: {},
    getElementById() { return null; },
    createElement() { const node = element(); created.push(node); return node; },
    addEventListener(name, handler) { this.handlers[name] = handler; },
    body: { appendChild() {} },
    documentElement: {
      async requestFullscreen() { doc.fullscreenElement = doc.documentElement; },
    },
    async exitFullscreen() { doc.fullscreenElement = null; },
  };
  const win = {
    innerWidth: 390, innerHeight: 830, handlers: {},
    matchMedia() { return { matches: true }; },
    addEventListener(name, cb) { this.handlers[name] = cb; }
  };
  const orientation = {
    async lock(value) { calls.push(value); },
    unlock() { calls.push('unlock'); },
    addEventListener() {}
  };
  vm.runInNewContext(code, { document: doc, window: win, screen: { orientation }, console });
  const button = created.find(x => x.id === 'svv-fullscreen');
  const hint = created.find(x => x.id === 'svv-landscape-hint');
  assert.ok(button && hint);
  const event = { preventDefault() {}, stopPropagation() {} };
  await button.handlers.click(event);
  assert.deepEqual(calls, ['landscape']);
  assert.equal(hint.style.display, 'block', 'portrait remains visible until device rotates');
  win.innerWidth = 830; win.innerHeight = 390;
  win.handlers.resize();
  assert.equal(hint.style.display, 'none');
  await button.handlers.click(event);
  assert.deepEqual(calls, ['landscape', 'unlock']);
});

test('bootstrap has bounded worker startup and a non-save-deleting recovery action', () => {
  const bootstrap = fs.readFileSync(path.resolve(__dirname, '../cloudflare/pages-bootstrap.html'), 'utf8');
  assert.match(bootstrap, /svv-web-handoff/);
  assert.match(bootstrap, /Làm mới trình tải/);
  assert.match(bootstrap, /registration\.unregister\(\)/);
  assert.match(bootstrap, /navigator\.serviceWorker\.controller/);
  assert.match(bootstrap, /timeout\(registration\.update\(\), 12000/);
});


test('first full game load saves immutable chunks and second load needs zero chunk downloads', async () => {
  const expected = Uint8Array.from({ length: 101 }, (_, i) => i);
  const chunks = [expected.slice(0, 16), expected.slice(16, 44), expected.slice(44)];
  const memory = new Map();
  const cold = await simulate(expected, chunks, { enableCache: true, cacheMemory: memory });
  const first = await cold.request('index.wasm');
  assert.deepEqual(Buffer.from(await first.arrayBuffer()), Buffer.from(expected));
  assert.equal(cold.fetches.filter(x => x.startsWith('/parts/')).length, 3);
  assert.equal(memory.size, 3, 'all successful chunks should be persisted after the first load');

  const warm = await simulate(expected, chunks, { enableCache: true, cacheMemory: memory });
  const second = await warm.request('index.wasm');
  assert.deepEqual(Buffer.from(await second.arrayBuffer()), Buffer.from(expected));
  assert.equal(warm.fetches.filter(x => x.startsWith('/parts/')).length, 0,
    'a refresh should read PCK/WASM parts locally, not fetch them again');

  const range = await warm.request('index.wasm', { Range: 'bytes=9-22' });
  assert.deepEqual(Buffer.from(await range.arrayBuffer()), Buffer.from(expected.slice(9, 23)));
  assert.equal(warm.fetches.filter(x => x.startsWith('/parts/')).length, 0);
});

test('cache write errors do not stop gameplay or corrupt normal network downloads', async () => {
  const expected = Uint8Array.from({ length: 33 }, (_, i) => i);
  const app = await simulate(expected, [expected.slice(0, 17), expected.slice(17)], {
    enableCache: true, failCachePut: true
  });
  const response = await app.request('index.wasm');
  assert.deepEqual(Buffer.from(await response.arrayBuffer()), Buffer.from(expected));
  assert.equal(app.cacheMemory.size, 0);
});
