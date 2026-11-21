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

const rescueImport = source.match(/const RESCUE_IMPORT_JS := """([\s\S]*?)"""/)[1];
const rescueRollback = source.match(/const RESCUE_ROLLBACK_JS := """([\s\S]*?)"""/)[1];
function rescueRuntime(initial = {}) {
  const data = new Map(Object.entries(initial));
  const r = runtime();
  r.context.localStorage = {
    getItem: key => data.has(key) ? data.get(key) : null,
    setItem: (key, value) => data.set(key, value),
    removeItem: key => data.delete(key),
  };
  r.data = data;
  r.importRescue = (key, payload) => vm.runInNewContext(rescueImport, r.context)(key, payload);
  r.rollbackRescue = () => vm.runInNewContext(rescueRollback, r.context);
  return r;
}

test('an explicit older imported profile replaces higher-sequence browser rescue', () => {
  const key = 'midgard_rescue_profile_offline';
  // The bridge must preserve encrypted bytes intact, not select by save_seq.
  const oldRescue = Buffer.from(JSON.stringify({settings: {save_seq: 900}})).toString('base64');
  const imported = Buffer.from(JSON.stringify({settings: {save_seq: 3}})).toString('base64');
  const r = rescueRuntime({[key]: oldRescue, unrelated: 'keep'});
  assert.equal(r.importRescue(key, imported), true);
  r.begin();
  assert.equal(r.data.get(key), imported);
  assert.equal(r.events.length, 0);
  r.writes[0].callback(null);
  assert.deepEqual(r.events, ['OK']);
  assert.equal(r.data.get(key), imported);
  assert.equal(r.data.get('unrelated'), 'keep');
});

test('failed IndexedDB import restores the exact previous rescue', () => {
  const key = 'midgard_rescue_profile_offline';
  const r = rescueRuntime({[key]: 'old-encrypted-bytes'});
  assert.equal(r.importRescue(key, 'imported-encrypted-bytes'), true);
  r.context.window._svvSaveSynced = status => {
    r.events.push(status);
    if (status !== 'OK') assert.equal(r.rollbackRescue(), true);
  };
  r.begin();
  r.writes[0].callback(new Error('quota'));
  assert.deepEqual(r.events, ['ERROR']);
  assert.equal(r.data.get(key), 'old-encrypted-bytes');
  assert.equal(r.context.window._svvRescueBeforeImport, undefined);
});

test('rollback removes a newly created rescue and leaves other profiles alone', () => {
  const r = rescueRuntime({other_profile: 'keep'});
  assert.equal(r.importRescue('new_profile', 'imported'), true);
  assert.equal(r.rollbackRescue(), true);
  assert.equal(r.data.has('new_profile'), false);
  assert.equal(r.data.get('other_profile'), 'keep');
});

test('unreadable or unwritable rescue fails before profile replacement', () => {
  const r = rescueRuntime({profile: 'old'});
  r.context.localStorage.getItem = () => { throw new Error('SecurityError'); };
  assert.equal(r.importRescue('profile', 'new'), false);
  assert.equal(r.data.get('profile'), 'old');
  const quota = rescueRuntime({profile: 'old'});
  quota.context.localStorage.setItem = () => { throw new Error('QuotaExceededError'); };
  assert.equal(quota.importRescue('profile', 'new'), false);
  assert.equal(quota.rollbackRescue(), true);
  assert.equal(quota.data.get('profile'), 'old');
});
