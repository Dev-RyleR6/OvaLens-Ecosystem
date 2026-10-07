import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import ts from 'typescript';

const pages = ['BatchesPage', 'ScanExplorerPage', 'AnalyticsPage', 'DevicesPage'];
const sources = Object.fromEntries(await Promise.all(pages.map(async page => [page, await readFile(new URL(`../src/pages/${page}.tsx`, import.meta.url), 'utf8')])));
const hatch = await readFile(new URL('../src/components/FinalizeHatchModal.tsx', import.meta.url), 'utf8');

function openingTags(source) {
  const file = ts.createSourceFile('page.tsx', source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const tags = [];
  function visit(node) {
    if (ts.isJsxOpeningElement(node) || ts.isJsxSelfClosingElement(node)) tags.push(node);
    ts.forEachChild(node, visit);
  }
  visit(file);
  return tags;
}
function attribute(tag, name) {
  return tag.attributes.properties.find(property => ts.isJsxAttribute(property) && property.name.getText() === name);
}

test('operational pages use shared header and action groups', () => {
  for (const [page, source] of Object.entries(sources)) {
    assert.match(source, /className="page-header"/, page);
    assert.match(source, /className="page-actions"/, page);
    assert.match(source, /className="secondary-action"/, page);
  }
});

test('purposeful lucide icons do not duplicate accessible labels', () => {
  for (const source of [...Object.values(sources), hatch]) {
    for (const tag of openingTags(source)) {
      if (tag.tagName.getText() === 'ArrowRight' || /^(RefreshCw|Plus|Search|Download|ChevronRight|ChevronLeft|Layers|FastForward|Clock|User|Zap|FileText|List|LayoutGrid|ArrowUpDown|ChevronDown|Activity|Trash2|CheckCircle2|Edit3|Cpu|Sliders|Save|X|AlertCircle|RotateCcw)$/.test(tag.tagName.getText())) {
        assert.equal(attribute(tag, 'aria-hidden')?.initializer?.text, 'true', tag.tagName.getText());
      }
    }
  }
});

test('table and grid selectors expose their current pressed state', () => {
  for (const page of ['BatchesPage', 'ScanExplorerPage']) {
    assert.match(sources[page], /aria-pressed=\{viewMode === 'TABLE'\}/);
    assert.match(sources[page], /aria-pressed=\{viewMode === 'GRID'\}/);
    assert.match(sources[page], /className="scan-grid"/);
  }
});

test('operational tables retain named keyboard-focusable internal scroll regions', () => {
  for (const page of ['BatchesPage', 'ScanExplorerPage', 'AnalyticsPage']) {
    const regions = openingTags(sources[page]).filter(tag => attribute(tag, 'role')?.initializer?.text === 'region');
    assert.ok(regions.length > 0, page);
    for (const region of regions) {
      assert.ok(attribute(region, 'aria-label'), page);
      assert.equal(attribute(region, 'tabIndex')?.initializer?.getText(), '{0}', page);
      assert.match(attribute(region, 'className')?.initializer?.text ?? '', /table-scroll/);
    }
    assert.match(sources[page], /min-w-\[\d+px\]/);
  }
});

test('sort controls announce the next direction using native buttons', () => {
  for (const page of ['BatchesPage', 'ScanExplorerPage']) {
    assert.match(sources[page], /<button className="action-link" onClick=\{\(\) => toggleSort/);
    assert.match(sources[page], /aria-label=\{`Sort .*ascending.*descending/);
    assert.match(sources[page], /aria-sort=/);
    assert.doesNotMatch(sources[page], /<th[^>]*tabIndex=/);
  }
});

test('batch selection is native and based on visible page membership', () => {
  const source = sources.BatchesPage;
  assert.match(source, /paginatedBatches\.every\(batch => selectedBatchIds\.includes\(batch\.batch_id\)\)/);
  assert.match(source, /type="checkbox" aria-label="Select all batches on this page"/);
  assert.match(source, /element\.indeterminate = somePageSelected && !allPageSelected/);
  assert.match(source, /previous\.filter\(id => !pageIds\.includes\(id\)\)/);
  assert.doesNotMatch(source, /selectedBatchIds\.length === paginatedBatches\.length/);
  assert.match(source, /<button className="secondary-action"[^\n]+Inspect<\/button>/);
  assert.match(source, /<button className="secondary-action"[^\n]+Analytics<\/button>/);
  assert.match(source, /<button className="secondary-action"[^\n]+Hatch<\/button>/);
  assert.match(source, /onClick=\{\(\) => \{ void handleSelectBatch\(b\); \}\}[\s\S]*?aria-label=\{`Open batch details for \$\{b\.batch_code\}`\}/);
  assert.doesNotMatch(source, /aria-label="View Official Candling Certificate"|<span>View Quality Certificate<\/span>/);
});

test('batch creation preserves the selected local midnight as a timezone-aware instant', () => {
  const source = sources.BatchesPage;
  assert.match(source, /type="date" required value=\{setDate\}/);
  const expression = source.match(/set_date: (new Date\(`\$\{setDate\}T00:00:00`\)\.toISOString\(\))/)?.[1];
  assert.ok(expression);
  for (const [timezone, date, expected] of [
    ['Asia/Manila', '2026-10-07', '2026-10-06T16:00:00.000Z'],
    ['Etc/UTC', '2026-10-07', '2026-10-07T00:00:00.000Z'],
    ['America/New_York', '2026-03-08', '2026-03-08T05:00:00.000Z'],
    ['America/New_York', '2026-03-09', '2026-03-09T04:00:00.000Z'],
  ]) {
    const result = spawnSync(process.execPath, ['-e', `const setDate = ${JSON.stringify(date)}; process.stdout.write(${expression});`], {
      env: { ...process.env, TZ: timezone }, encoding: 'utf8',
    });
    assert.equal(result.status, 0, result.stderr);
    assert.equal(result.stdout, expected, `${timezone}: ${date}`);
  }
  assert.match(source, /grid-cols-1 sm:grid-cols-2 gap-3/);
});

test('pending review badges follow recorded routing rather than model confidence', () => {
  const badges = openingTags(sources.ScanExplorerPage).filter(tag =>
    tag.tagName.getText() === 'Badge' && attribute(tag, 'value')?.initializer?.text === 'MANUAL_REVIEW'
  );
  assert.equal(badges.length, 2);
  for (const badge of badges) {
    assert.ok(ts.isBinaryExpression(badge.parent));
    const pendingReview = new Function('scan', `return ${badge.parent.left.getText()};`);
    for (const [scan, expected] of [
      [{ confidence: 0.5, routing_action: 'ACCEPT', is_overridden: true }, false],
      [{ confidence: 0.5, routing_action: 'REJECT', is_overridden: true }, false],
      [{ confidence: 0.95, routing_action: 'MANUAL_REVIEW' }, true],
      [{ confidence: 0.5, routing_action: 'MANUAL_REVIEW' }, true],
      [{ confidence: 0.5 }, false],
    ]) assert.equal(pendingReview(scan), expected);
  }
  assert.equal((sources.ScanExplorerPage.match(/>Low confidence<\/span>/g) ?? []).length, 2);
});

test('scan corrections announce success and preserve server search semantics', () => {
  const source = sources.ScanExplorerPage;
  assert.match(source, /role="status" className="p-3\.5 bg-emerald-50/);
  assert.equal((source.match(/Badge value="OVERRIDDEN"/g) ?? []).length, 2);
  assert.match(source, /apiClient\.searchScans\(/);
  assert.match(source, /requestRef\.current\?\.abort\(\)/);
  assert.match(source, /offset: \(currentPage - 1\) \* rowsPerPage/);
});

test('scan diagnostics render only recorded values and explicit unavailable states', () => {
  const source = sources.ScanExplorerPage;
  assert.match(source, /JSON\.stringify\(selectedScan\.detections, null, 2\)/);
  assert.match(source, /Detection telemetry unavailable\. No raw detections were recorded for this scan\./);
  assert.doesNotMatch(source, /bbox:\s*\[/);
  assert.doesNotMatch(source, /24\.6|0\.95|0\.78/);
  assert.doesNotMatch(source, /(?:sequence_number|inference_ms|confidence|aspect_ratio)\s*\?\?/);
  assert.match(source, /Number\.isFinite\(scan\.inference_ms\) \? `\$\{scan\.inference_ms\.toFixed\(1\)\} ms` : '—'/);
  assert.match(source, /Number\.isFinite\(scan\.sequence_number\).*: '—'/);
  assert.match(source, /inferenceMs=\{Number\.isFinite\(selectedScan\.inference_ms\) \? selectedScan\.inference_ms : undefined\}/);
  assert.match(source, /confidence=\{Number\.isFinite\(selectedScan\.confidence\) \? selectedScan\.confidence : undefined\}/);
  assert.match(source, /sequenceNumber=\{selectedScan\.sequence_number\}/);
  assert.match(source, /aspectRatio=\{selectedScan\.aspect_ratio\}/);
  assert.match(source, /: `Scan \$\{scan\.scan_id\}`/);
  assert.match(source, /No conveyor routing action was recorded for this scan/);
  assert.doesNotMatch(source, /routing_action === 'ACCEPT' \|\| selectedScan\.final_class/);
});

test('device sliders are disabled and explained for read-only operators', () => {
  const ranges = openingTags(sources.DevicesPage).filter(tag => attribute(tag, 'type')?.initializer?.text === 'range');
  assert.equal(ranges.length, 3);
  for (const range of ranges) {
    assert.match(attribute(range, 'disabled')?.initializer?.getText() ?? '', /!canCalibrate/);
    assert.ok(attribute(range, 'aria-describedby'));
  }
  assert.match(sources.DevicesPage, /Only administrators and managers can edit calibration records/);
});

test('finalizing hatch results preserves counts and scrolls within the viewport', () => {
  assert.match(hatch, /setHatchedCount\(batch\?\.hatched_count \?\? 0\)/);
  assert.match(hatch, /\{displayBatch\.fertile_count\} eggs/);
  assert.match(hatch, /aria-label="Close hatch results dialog" disabled=\{isSubmitting\}/);
  assert.match(hatch, /<form[^>]*min-h-0 overflow-y-auto overscroll-contain/);
  assert.match(hatch, /max-h-\[calc\(100dvh-1\.5rem\)\]/);
  assert.match(hatch, /if \(isSubmitting\) return/);
});
