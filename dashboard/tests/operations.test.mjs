import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';

// Exercise the shipped TypeScript helpers with Node's runner; no extra test dependency.
async function loadHelper(path) {
  const source = await readFile(new URL(path, import.meta.url), 'utf8');
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 },
  });
  return import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);
}
const { deviceAvailability } = await loadHelper('../src/lib/deviceStatus.ts');
const { readPreferences, savePreferences } = await loadHelper('../src/lib/preferences.ts');

test('a stored online flag requires a recent, valid heartbeat', () => {
  const now = Date.parse('2026-10-07T04:00:00Z');
  assert.equal(deviceAvailability({ status: 'ONLINE' }, now), 'UNKNOWN');
  assert.equal(deviceAvailability({ status: 'ONLINE', last_heartbeat: 'invalid' }, now), 'UNKNOWN');
  assert.equal(deviceAvailability({ status: 'ONLINE', last_heartbeat: '2026-10-07T03:58:00Z' }, now), 'STALE');
  assert.equal(deviceAvailability({ status: 'ONLINE', last_heartbeat: '2026-10-07T04:00:30Z' }, now), 'STALE');
  assert.equal(deviceAvailability({ status: 'ONLINE', last_heartbeat: '2026-10-07T03:59:45Z' }, now), 'ONLINE');
  assert.equal(deviceAvailability({ status: 'SCANNING', last_heartbeat: '2026-10-07T03:59:45Z' }, now), 'SCANNING');
  assert.equal(deviceAvailability({ status: 'ERROR', last_heartbeat: '2026-10-07T03:59:45Z' }, now), 'ERROR');
});

test('manual refresh survives saving and reloading preferences', () => {
  const storage = new Map();
  globalThis.localStorage = { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value) };
  globalThis.window = new EventTarget();
  let changed = 0;
  window.addEventListener('ovalens-preferences', () => changed++);
  assert.equal(readPreferences().pollingInterval, 10);
  savePreferences({ pollingInterval: 0, theme: 'dark', tableDensity: 'compact' });
  assert.deepEqual(readPreferences(), { pollingInterval: 0, theme: 'dark', tableDensity: 'compact' });
  assert.equal(changed, 1);
  storage.set('ovalens_polling_interval', '-1');
  storage.set('ovalens_theme', 'invalid');
  storage.set('ovalens_table_density', 'invalid');
  assert.deepEqual(readPreferences(), { pollingInterval: 10, theme: 'light', tableDensity: 'comfortable' });
});
