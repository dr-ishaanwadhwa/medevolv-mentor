// Tooltip coverage check (PRD R3). Scans apps/web/src with the TypeScript compiler API and reports controls
// that have no tooltip. It fails only on NEW gaps (and on baseline entries that no longer exist, so the
// baseline shrinks honestly). `--update` rewrites tips-baseline.json from the current scan.
//
// A gap is:
//   kit      <Button|LinkButton|Chip|CitationChip> without a `tip` prop
//   raw      <button>, <a>, <Link>, role="button|radio|option|tab", <input type="radio|checkbox"> that is
//            neither the direct child of <Tooltip> nor carries `data-tip-id`
//   no-tip   tip={NO_TIP} (or tip="__no_tip__") without a comment on the same or the previous line
import { readFileSync, readdirSync, statSync, writeFileSync, existsSync } from 'node:fs';
import { dirname, join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

const here = dirname(fileURLToPath(import.meta.url));
const SRC = join(here, '..', 'src');
const BASELINE = join(here, 'tips-baseline.json');

const KIT = new Set(['Button', 'LinkButton', 'Chip', 'CitationChip']);
const RAW = new Set(['button', 'a', 'Link']);
const ROLES = new Set(['button', 'radio', 'option', 'tab']);
// The kit's own implementations render the raw element the kit wraps.
const KIT_FILES = new Set([
  'components/ui/Button.tsx',
  'components/ui/Chip.tsx',
  'components/ui/CitationChip.tsx',
  'components/ui/Tooltip.tsx',
]);

function attrsOf(node) {
  const el = ts.isJsxElement(node) ? node.openingElement : node;
  const out = new Map();
  for (const a of el.attributes.properties) {
    if (ts.isJsxAttribute(a)) out.set(a.name.getText(), a);
  }
  return out;
}

const strValue = (a) => (a && a.initializer && ts.isStringLiteral(a.initializer) ? a.initializer.text : undefined);

/** @returns {{rule:string, tag:string, line:number}[]} */
export function scanSource(rel, text) {
  const sf = ts.createSourceFile(rel, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const lines = text.split('\n');
  const found = [];
  const add = (rule, tag, node) =>
    found.push({ rule, tag, line: sf.getLineAndCharacterOfPosition(node.getStart()).line + 1 });

  const inTooltip = (node) => {
    // The direct JSX parent must be <Tooltip>.
    let p = node.parent;
    while (p && ts.isParenthesizedExpression(p)) p = p.parent;
    return !!p && ts.isJsxElement(p) && p.openingElement.tagName.getText() === 'Tooltip';
  };

  const visit = (node) => {
    if (ts.isJsxElement(node) || ts.isJsxSelfClosingElement(node)) {
      const opening = ts.isJsxElement(node) ? node.openingElement : node;
      const tag = opening.tagName.getText();
      const attrs = attrsOf(node);
      const tipAttr = attrs.get('tip');

      if (KIT.has(tag) && !KIT_FILES.has(rel) && !tipAttr) add('kit', tag, opening);

      if (tipAttr) {
        const init = tipAttr.initializer;
        const isNoTip =
          (init && ts.isStringLiteral(init) && init.text === '__no_tip__') ||
          (init && ts.isJsxExpression(init) && init.expression && init.expression.getText() === 'NO_TIP');
        if (isNoTip) {
          const ln = sf.getLineAndCharacterOfPosition(tipAttr.getStart()).line;
          const near = [lines[ln] ?? '', lines[ln - 1] ?? ''];
          if (!near.some((l) => /\/\/|\/\*/.test(l))) add('no-tip', tag, tipAttr);
        }
      }

      if (!KIT_FILES.has(rel) && !KIT.has(tag)) {
        const role = strValue(attrs.get('role'));
        const type = strValue(attrs.get('type'));
        const rawControl =
          RAW.has(tag) ||
          (role && ROLES.has(role)) ||
          (tag === 'input' && (type === 'radio' || type === 'checkbox'));
        if (rawControl && !attrs.has('data-tip-id') && !tipAttr && !inTooltip(node)) {
          add('raw', role ? `${tag}[role=${role}]` : tag, opening);
        }
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);

  const seen = new Map();
  return found.map((g) => {
    const k = `${rel}|${g.rule}|${g.tag}`;
    const n = (seen.get(k) ?? 0) + 1;
    seen.set(k, n);
    return { ...g, key: `${k}|${n}` };
  });
}

function* walk(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) yield* walk(p);
    else if (/\.tsx$/.test(name) && !/\.test\.tsx$/.test(name)) yield p;
  }
}

export function scanAll() {
  const gaps = [];
  for (const file of walk(SRC)) {
    const rel = relative(SRC, file).split(sep).join('/');
    gaps.push(...scanSource(rel, readFileSync(file, 'utf8')));
  }
  return gaps;
}

function main() {
  const gaps = scanAll();
  const keys = gaps.map((g) => g.key).sort();
  if (process.argv.includes('--update')) {
    writeFileSync(BASELINE, JSON.stringify({ gaps: keys }, null, 2) + '\n');
    console.log(`check-tips: baseline written (${keys.length} gaps)`);
    return;
  }
  const baseline = new Set(existsSync(BASELINE) ? JSON.parse(readFileSync(BASELINE, 'utf8')).gaps : []);
  const current = new Set(keys);
  const fresh = gaps.filter((g) => !baseline.has(g.key));
  const stale = [...baseline].filter((k) => !current.has(k));
  if (fresh.length) {
    console.error(`check-tips: ${fresh.length} new control(s) without a tooltip:`);
    for (const g of fresh) console.error(`  src/${g.key.split('|')[0]}:${g.line}  <${g.tag}> (${g.rule})`);
    console.error('Add a `tip` (kit controls) or wrap in <Tooltip> / set data-tip-id (raw controls).');
  }
  if (stale.length) {
    console.error(`check-tips: ${stale.length} baseline entr${stale.length === 1 ? 'y' : 'ies'} no longer exist (good). Run: node scripts/check-tips.mjs --update`);
    for (const k of stale) console.error(`  ${k}`);
  }
  if (fresh.length || stale.length) process.exit(1);
  console.log(`check-tips: ok (${gaps.length} gaps, all in baseline)`);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) main();
