import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';

test('batch UI copy does not contain UTF-8 text decoded as Windows-1252', async () => {
  for (const path of ['../src/pages/BatchesPage.tsx', '../src/components/BatchIncubationStatus.tsx']) {
    const text = await readFile(new URL(path, import.meta.url), 'utf8');
    assert.doesNotMatch(text, /\u00c2[\u0080-\u00bf]|\u00e2[\u20ac\u201a]/, path);
  }
});

const source = await readFile(new URL('../src/components/BatchIncubationStatus.tsx', import.meta.url), 'utf8');
let { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020 },
});
outputText = outputText.replace(/import \{ Badge \} from ['"]\.\/Badge['"];?/, 'const Badge = props => props;');
outputText = outputText.replaceAll('"react/jsx-runtime"', JSON.stringify(new URL('../node_modules/react/jsx-runtime.js', import.meta.url).href));
const { BatchIncubationStatus } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);

test('completed and archived batches show a single final status without a repeated checkpoint', () => {
  for (const status of ['COMPLETED', 'ARCHIVED']) {
    const rendered = BatchIncubationStatus({ batch: { status, current_stage: 'COMPLETED', milestone_alert: null } });
    assert.equal(rendered.props.children[0].props.value, status);
    assert.equal(rendered.props.children[1], false);
  }
});

test('overdue hatch records take precedence while retaining the recorded candling checkpoint', () => {
  const rendered = BatchIncubationStatus({ batch: {
    status: 'CANDLING_DUE', current_stage: 'DAY_10', milestone_alert: 'HATCH DUE: Day 28 Final Hatch Record Pending',
  } });
  assert.equal(rendered.props.children[0].props.value, 'HATCH DUE');
  assert.equal(rendered.props.children[1].props.children, 'Day 10 candling');
  assert.equal(rendered.props.title, 'HATCH DUE: Day 28 Final Hatch Record Pending');
});
