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
const { batchLabelLines, operationalChartData } = await loadHelper('../src/lib/chartData.ts');

test('paired charts preserve identical batch order, zero scans and repeated scan counts', () => {
  const rows = [
    { batch_code: 'UNSCANNED', initial_egg_count: 500, total_scanned: 0, fertile_count: 0, infertile_count: 0 },
    { batch_code: 'REPEATED', initial_egg_count: 500, total_scanned: 534, fertile_count: 440, infertile_count: 94 },
    { batch_code: 'INFERTILE-ONLY', initial_egg_count: 10, total_scanned: 10, fertile_count: 0, infertile_count: 10 },
  ];
  const chart = operationalChartData(rows);
  assert.deepEqual(chart.classification.map(row => row.batch), rows.map(row => row.batch_code));
  assert.deepEqual(chart.comparison.map(row => row.batch), rows.map(row => row.batch_code));
  assert.equal(chart.classification[0].total, 0);
  assert.equal(chart.comparison[1].Scanned, 534);
  assert.equal(chart.comparison[1].Set, 500);
  for (const row of chart.classification) assert.equal(row.Fertile + row.Infertile, row.total);
  assert.ok(chart.maximum >= 534);
  assert.equal(chart.ticks[0], 0);
  assert.equal(chart.ticks.at(-1), chart.maximum);
});

test('count axes remain finite integer scales for empty, small and large selections', () => {
  for (const count of [0, 1, 3, 9, 534, 600, 15000]) {
    const chart = operationalChartData(count ? [{ batch_code: 'B', initial_egg_count: count, total_scanned: count, fertile_count: count, infertile_count: 0 }] : []);
    assert.ok(Number.isFinite(chart.maximum) && chart.maximum >= Math.max(1, count));
    assert.ok(chart.ticks.every(Number.isInteger));
    assert.ok(chart.ticks.length >= 2 && chart.ticks.length <= 6);
  }
});

test('chart labels preserve complete identifiers within bounded lines', () => {
  for (const label of ['BATCH-2026-08-KAY-01', 'BATCH-2026-07-KHK-01', 'X'.repeat(64), 'A-B-C-D-E-F-G-H-I-J-K-L-M-N-O-P']) {
    const lines = batchLabelLines(label);
    assert.equal(lines.join(''), label);
    assert.ok(lines.every(line => line.length <= 17));
  }
});

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
