// Node-runnable unit tests for the LIVE indicator's pure formatter.
//
// Run from repo root:
//   node tests/terminal/test_live_stamp.cjs
//
// Exits 0 on success, 1 on the first failing assertion.
//
// The deployed live-stamp-format.js is a UMD-style IIFE intended for browsers
// (<script> tag, no module system). We load its source here and evaluate it
// in a sandbox with a synthetic `module` so the CJS export branch fires.
// This avoids depending on Node's package.json type:module detection, which
// varies based on parent directories in the test environment.

const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const SRC_PATH = path.join(__dirname, '..', '..', 'docs', 'terminal', 'live-stamp-format.js');
const source = fs.readFileSync(SRC_PATH, 'utf8');

const sandbox = { module: { exports: {} }, console, Date, Intl };
vm.createContext(sandbox);
vm.runInContext(source, sandbox);

const { formatLiveStamp, liveStampState, STALE_MS } = sandbox.module.exports;

function run(name, fn) {
  try {
    fn();
    console.log('  ok  ' + name);
  } catch (err) {
    console.error('  FAIL  ' + name);
    console.error(err.stack || err.message);
    process.exit(1);
  }
}

run('STALE_MS is 24 hours', () => {
  assert.strictEqual(STALE_MS, 24 * 60 * 60 * 1000);
});

run('returns LIVE when generated_at is fresh', () => {
  const now = new Date('2026-05-16T21:33:00Z');
  const stamp = formatLiveStamp('2026-05-16T21:32:00Z', now);
  assert.strictEqual(stamp.label, 'LIVE');
  assert.strictEqual(stamp.dot, '#5fd28a');
  assert.ok(stamp.text && stamp.text.length > 0);
});

run('still LIVE after 1 hour (well within the 24 h tolerance)', () => {
  const now = new Date('2026-05-16T22:32:00Z');
  const stamp = formatLiveStamp('2026-05-16T21:32:00Z', now);
  assert.strictEqual(stamp.label, 'LIVE');
});

run('still LIVE after 12 hours', () => {
  const now = new Date('2026-05-17T09:32:00Z');
  const stamp = formatLiveStamp('2026-05-16T21:32:00Z', now);
  assert.strictEqual(stamp.label, 'LIVE');
});

run('returns STALE after 25 hours (past the 24 h threshold)', () => {
  const now = new Date('2026-05-17T22:32:00Z');
  const stamp = formatLiveStamp('2026-05-16T21:32:00Z', now);
  assert.strictEqual(stamp.label, 'STALE');
  assert.strictEqual(stamp.dot, '#e0a23a');
});

run('returns LIVE right at the boundary (1 ms before 24 h)', () => {
  const now = new Date(Date.parse('2026-05-16T21:32:00Z') + (24 * 60 * 60 * 1000 - 1));
  const stamp = formatLiveStamp('2026-05-16T21:32:00Z', now);
  assert.strictEqual(stamp.label, 'LIVE');
});

run('returns OFFLINE for null/undefined generated_at', () => {
  const stamp1 = formatLiveStamp(null, new Date());
  const stamp2 = formatLiveStamp(undefined, new Date());
  assert.strictEqual(stamp1.label, 'OFFLINE');
  assert.strictEqual(stamp1.text, '—');
  assert.strictEqual(stamp2.label, 'OFFLINE');
});

run('returns OFFLINE for non-parseable string', () => {
  const stamp = formatLiveStamp('not-a-date', new Date());
  assert.strictEqual(stamp.label, 'OFFLINE');
});

run('liveStampState exposes age and parsed time', () => {
  const now = new Date('2026-05-16T21:35:00Z');
  const state = liveStampState('2026-05-16T21:32:00Z', now);
  assert.strictEqual(state.kind, 'live');
  assert.strictEqual(state.ageMs, 3 * 60 * 1000);
  assert.strictEqual(state.when.toISOString(), '2026-05-16T21:32:00.000Z');
});

run('liveStampState flips to stale once past 24 h', () => {
  const now = new Date(Date.parse('2026-05-16T21:32:00Z') + 24 * 60 * 60 * 1000 + 1000);
  const state = liveStampState('2026-05-16T21:32:00Z', now);
  assert.strictEqual(state.kind, 'stale');
});

run('does not crash if Intl throws (text falls back to ISO)', () => {
  const sb = { module: { exports: {} }, console, Date,
    Intl: { DateTimeFormat: function () { throw new Error('forced'); } } };
  vm.createContext(sb);
  vm.runInContext(source, sb);
  const f = sb.module.exports.formatLiveStamp;
  const stamp = f('2026-05-16T21:32:00Z', new Date('2026-05-16T21:33:00Z'));
  assert.strictEqual(stamp.label, 'LIVE');
  assert.strictEqual(stamp.text, '2026-05-16T21:32:00.000Z');
});

console.log('\nall live-stamp tests passed');
