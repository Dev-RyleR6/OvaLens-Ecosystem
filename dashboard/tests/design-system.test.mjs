import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';

const source = path => readFile(new URL(path, import.meta.url), 'utf8');

async function loadComponent(path) {
  const { outputText } = ts.transpileModule(await source(path), {
    compilerOptions: { module: ts.ModuleKind.ESNext, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020 },
  });
  const reactRuntime = new URL('../node_modules/react/jsx-runtime.js', import.meta.url).href;
  return import(`data:text/javascript;base64,${Buffer.from(outputText.replaceAll('"react/jsx-runtime"', JSON.stringify(reactRuntime))).toString('base64')}`);
}

const { Badge } = await loadComponent('../src/components/Badge.tsx');

test('status badges keep biological classes separate from review and account roles', () => {
  for (const [type, value, label, tone] of [
    ['fertility', 'FERTILE', 'Fertile', 'status-success'],
    ['fertility', 'INFERTILE', 'Infertile', 'status-danger'],
    ['status', 'MANUAL_REVIEW', 'Awaiting review', 'status-warning'],
    ['role', 'ADMIN', 'Administrator', 'status-neutral'],
    ['role', 'MANAGER', 'Manager', 'status-neutral'],
    ['role', 'OPERATOR', 'Operator', 'status-neutral'],
    ['stage', 'DAY_10', 'Day 10 (Candling)', 'status-neutral'],
    ['status', 'CANDLING_DUE', 'Candling due', 'status-warning'],
    ['status', 'ACTIVE', 'Active', 'status-success'],
    ['status', 'INACTIVE', 'Suspended', 'status-neutral'],
  ]) {
    const badge = Badge({ type, value });
    assert.equal(badge.props.children, label);
    assert.ok(badge.props.className.includes(tone));
    assert.ok(badge.props.className.includes('status-badge'));
  }
});

test('typography uses only self-hosted Latin Plex weights and distinct metadata size', async () => {
  const main = await source('../src/main.tsx');
  assert.equal((main.match(/@fontsource\/ibm-plex-sans\/latin-(400|500|600|700)\.css/g) ?? []).length, 4);
  assert.doesNotMatch(main, /plus-jakarta|fonts\.googleapis/);
  const config = await source('../tailwind.config.js');
  assert.match(config, /IBM Plex Sans/);
  assert.match(config, /xs: \['\.75rem'/);
});

test('shared controls have explicit supported colors and touch-safe dimensions', async () => {
  const button = await source('../src/components/ui/button.tsx');
  assert.doesNotMatch(button, /bg-accent|h-8|h-9/);
  assert.match(await source('../tailwind.config.js'), /destructive: \{ DEFAULT: '#DC2626', foreground: '#FFFFFF'/);
  assert.match(button, /min-h-11/);
  assert.match(await source('../src/index.css'), /select, textarea \{ font-size: 16px !important; \}/);
  for (const component of ['input', 'select']) {
    const text = await source(`../src/components/ui/${component}.tsx`);
    assert.match(text, /min-h-11/);
    assert.match(text, /bg-card/);
    assert.match(text, /text-base sm:text-sm/);
  }
});

test('backup blobs use the shared authenticated transport and escaped filename', async () => {
  const client = await source('../src/api/client.ts');
  assert.match(client, /downloadBackup: async \(filename: string\): Promise<Blob>/);
  assert.match(client, /api\.get<Blob>\(`\/settings\/backups\/\$\{encodeURIComponent\(filename\)\}\/download`, \{ responseType: 'blob' \}\)/);
});

test('printable records preserve zero counts without invented certification', async () => {
  const certificate = await source('../src/components/CandlingCertificateModal.tsx');
  assert.match(certificate, /fertile_count \?\? 0/);
  assert.match(certificate, /total_scanned \?\? 0/);
  assert.doesNotMatch(certificate, /451|95\.4%|100% SORTED|STATION-01-RP5/);
  assert.match(certificate, /totalScanned > 0/);
  const css = await source('../src/index.css');
  assert.match(css, /body:has\(\.candling-record\) #root \{ display: none; \}/);
});

test('pending corrections cannot be dismissed through alternate controls', async () => {
  const modal = await source('../src/components/HumanInTheLoopOverrideModal.tsx');
  assert.doesNotMatch(modal, /onClick=\{onClose\}/);
  assert.match(modal, /aria-label="Close classification correction"/);
  assert.match(modal, /aria-pressed=\{reason === preset\}/);
});
