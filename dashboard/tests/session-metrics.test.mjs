import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';

const source = await readFile(new URL('../src/utils/sessionMetrics.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText;
const { estimateCapacity, formatRunDuration } = await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);

test('capacity uses full precision, whole scans, and positive finite input', () => {
  assert.equal(estimateCapacity(120, 600, '30'), 360);
  assert.equal(estimateCapacity(1, 100, '.5'), 0);
  assert.equal(estimateCapacity(1, .5, '.1'), 12);
  for (const input of ['', ' ', '0', '-1', 'NaN', 'Infinity', '1e309', 'bad']) {
    assert.equal(estimateCapacity(120, 600, input), null, input);
  }
  for (const seconds of [null, 0, -1]) assert.equal(estimateCapacity(120, seconds, '10'), null);
  assert.equal(estimateCapacity(0, 600, '10'), null);
});

test('saved duration formats hours without wrapping at 24 hours', () => {
  assert.equal(formatRunDuration(600), '00:10:00');
  assert.equal(formatRunDuration(.5), '00:00:00.5');
  assert.equal(formatRunDuration(90061), '25:01:01');
  assert.equal(formatRunDuration(null), 'Unavailable');
});
