'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../original-addons/web_save_manager.gd'), 'utf8');
const bridge = source.match(/const IMPORT_SYNC_JS := """([\s\S]*?)"""/)[1];

function runtime({persistent = true, syncing = false} = {}) {
  const events = [], timers = [], writes = [];
  const context = {
    Date: {now: () => 1000},
    GodotFS: {_syncing: syncing, is_persistent: () => persistent},
    FS: {syncfs: (populate, callback) => writes.push({populate, callback})},
    window: {_svvSaveSynced: state => events.push(state)},
    setTimeout: callback => timers.push(callback),
  };
  return {events, timers, writes, context, begin: () => vm.runInNewContext(bridge, context)};
}

test('import persistence waits for an in-flight flush and actual IndexedDB callback', () => {
  const r = runtime({syncing: true});
  assert.equal(r.begin(), true);
  assert.equal(r.writes.length, 0);
  assert.deepEqual(r.events, []);
  r.context.GodotFS._syncing = false;
  r.timers.shift()();
  assert.equal(r.writes.length, 1);
  assert.equal(r.writes[0].populate, false);
  assert.equal(r.context.GodotFS._syncing, true);
  assert.deepEqual(r.events, []); // No reload/completion before durability.
  r.writes[0].callback(null);
  assert.deepEqual(r.events, ['OK']);
  assert.equal(r.context.GodotFS._syncing, false);
});

test('quota failure reports error instead of successful import/reload', () => {
  const r = runtime();
  r.begin();
  r.writes[0].callback(new Error('QuotaExceededError'));
  assert.deepEqual(r.events, ['ERROR']);
  assert.equal(r.context.GodotFS._syncing, false);
});

test('persistent storage unavailable and missing engine bridge fail closed', () => {
  const r = runtime({persistent: false});
  assert.equal(r.begin(), false);
  assert.equal(r.writes.length, 0);
  assert.equal(vm.runInNewContext(bridge, {}), false);
});

test('a stalled existing flush times out without starting overlapping writes', () => {
  const r = runtime({syncing: true});
  r.begin();
  r.context.Date.now = () => 32000;
  r.timers.shift()();
  assert.deepEqual(r.events, ['TIMEOUT']);
  assert.equal(r.writes.length, 0);
});
