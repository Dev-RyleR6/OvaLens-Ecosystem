import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';

const pages = Object.fromEntries(await Promise.all(['SettingsPage', 'UsersPage', 'LoginPage'].map(async name => [name, await readFile(new URL(`../src/pages/${name}.tsx`, import.meta.url), 'utf8')])));
const syntax = Object.fromEntries(Object.entries(pages).map(([name, source]) => [name, ts.createSourceFile(`${name}.tsx`, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)]));

function elements(file) {
  const result = [];
  const visit = node => {
    if (ts.isJsxOpeningElement(node) || ts.isJsxSelfClosingElement(node)) result.push(node);
    ts.forEachChild(node, visit);
  };
  visit(file);
  return result;
}
function attribute(node, name) {
  return node.attributes.properties.find(item => ts.isJsxAttribute(item) && item.name.getText() === name)?.initializer?.getText();
}

test('account pages use the shared operational header and action vocabulary', () => {
  for (const source of Object.values(pages)) {
    assert.match(source, /className="page-header/);
    assert.match(source, /className="page-actions/);
    assert.match(source, /primary-action/);
    assert.doesNotMatch(source, /animate-shake|hover:scale|animate-in/);
  }
});

test('lucide icons on account pages are hidden from assistive technology', () => {
  for (const file of Object.values(syntax)) {
    const icons = new Set(['Icon']);
    for (const statement of file.statements) {
      if (ts.isImportDeclaration(statement) && statement.moduleSpecifier.text === 'lucide-react') {
        for (const binding of statement.importClause.namedBindings.elements) icons.add(binding.name.text);
      }
    }
    for (const node of elements(file)) {
      if (icons.has(node.tagName.getText())) assert.equal(attribute(node, 'aria-hidden'), '"true"', `${file.fileName}: ${node.tagName.getText()}`);
    }
  }
});

test('user cards use available-space grid and shared role/status badges', () => {
  assert.match(pages.UsersPage, /className="scan-grid"/);
  assert.doesNotMatch(pages.UsersPage, /lg:grid-cols-3|md:grid-cols-2|w-28|w-24/);
  assert.ok((pages.UsersPage.match(/\[overflow-wrap:anywhere\]/g) || []).length >= 4);
  for (const name of ['UsersPage', 'SettingsPage']) {
    assert.match(pages[name], /<Badge type="role"/);
    assert.match(pages[name], /<Badge value=\{[^}]+\? 'ACTIVE' : 'INACTIVE'\}/);
  }
});

test('tables expose named focusable scrolling regions and semantic column headers', () => {
  for (const name of ['UsersPage', 'SettingsPage']) {
    const nodes = elements(syntax[name]);
    const scrolls = nodes.filter(node => attribute(node, 'className')?.includes('table-scroll'));
    assert.ok(scrolls.length > 0);
    for (const node of scrolls) {
      assert.equal(attribute(node, 'tabIndex'), '{0}');
      assert.equal(attribute(node, 'role'), '"region"');
      assert.match(attribute(node, 'aria-label'), /table, scroll horizontally/);
    }
    for (const node of nodes.filter(node => node.tagName.getText() === 'th')) assert.ok(attribute(node, 'scope'));
  }
  assert.match(pages.UsersPage, /aria-sort=\{selected \? \(sortOrder === 'asc' \? 'ascending' : 'descending'\) : 'none'\}/);
  assert.match(pages.UsersPage, /aria-label=\{`Sort \$\{label\} \$\{nextDirection\}`\}/);
  assert.match(pages.UsersPage, /sortOrder === 'asc' \? ArrowUp : ArrowDown/);
  assert.match(pages.UsersPage, /aria-pressed=\{viewMode === 'TABLE'\}/);
  assert.match(pages.UsersPage, /aria-pressed=\{viewMode === 'GRID'\}/);
});

test('user loading, stale refresh, and filtered-empty states are distinct', () => {
  assert.match(pages.UsersPage, /Loading user accounts…/);
  assert.match(pages.UsersPage, /isError && hasLoaded/);
  assert.match(pages.UsersPage, /Previously loaded accounts are shown and may be out of date/);
  assert.match(pages.UsersPage, /isError && !hasLoaded/);
  assert.match(pages.UsersPage, /hasFilters \? 'No matching users' : 'No user accounts'/);
  assert.match(pages.UsersPage, /actionLabel=\{hasFilters \? 'Clear filters'/);
});

test('facility errors stay inside settings navigation and backups have independent recovery', () => {
  const source = pages.SettingsPage;
  assert.doesNotMatch(source, /if \(isError && activeTab === 'facility'/);
  assert.ok(source.indexOf('aria-label="Settings sections"') < source.indexOf('title="Settings Service Offline"'));
  for (const section of ['facility', 'account', 'backups', 'preferences']) assert.match(source, new RegExp(`aria-pressed=\\{activeTab === '${section}'\\}`));
  assert.match(source, /backupListError &&/);
  assert.match(source, /hasLoadedBackups && backups.length === 0/);
  assert.match(source, /Retry loading archives/);
  assert.match(source, /apiClient\.downloadBackup\(filename\)/);
  assert.match(source, /URL\.createObjectURL\(blob\)/);
  assert.match(source, /URL\.revokeObjectURL\(objectUrl\)/);
  assert.match(source, /Retry download/);
  assert.doesNotMatch(source, /href=\{apiClient\.downloadBackupUrl|axios|Bearer/);
});

test('password visibility controls are centered, named and expose pressed state', () => {
  for (const [name, count] of [['SettingsPage', 2], ['LoginPage', 1]]) {
    const controls = elements(syntax[name]).filter(node => node.tagName.getText() === 'button' && attribute(node, 'aria-label')?.includes('password'));
    assert.equal(controls.length, count);
    for (const node of controls) {
      assert.match(attribute(node, 'aria-label'), /Hide.*password.*Show.*password/);
      assert.ok(attribute(node, 'aria-pressed'));
      assert.match(attribute(node, 'className'), /top-1\/2 -translate-y-1\/2/);
      assert.match(attribute(node, 'className'), /flex items-center justify-center/);
    }
  }
});

test('sign in preserves the exact password while normalizing the email', () => {
  assert.match(pages.LoginPage, /await login\(\{ email: cleanEmail, password \}\)/);
  assert.match(pages.LoginPage, /sanitize\(email\)\.toLowerCase\(\)/);
  assert.doesNotMatch(pages.LoginPage, /password\.trim\(\)|cleanPassword|sanitize\(password\)/);
});
