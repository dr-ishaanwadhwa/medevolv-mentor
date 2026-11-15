import { describe, expect, it } from 'vitest';
import { scanSource } from './check-tips.mjs';

const scan = (src) => scanSource('components/x/Fixture.tsx', src).map((g) => `${g.rule}:${g.tag}`);

describe('check-tips rules', () => {
  it('kit control without tip fails', () => {
    expect(scan(`export const A = () => <Button>Foo</Button>;`)).toEqual(['kit:Button']);
    expect(scan(`export const A = () => <LinkButton href="/">Foo</LinkButton>;`)).toEqual(['kit:LinkButton']);
    expect(scan(`export const A = () => <Chip>Foo</Chip>;`)).toEqual(['kit:Chip']);
    expect(scan(`export const A = () => <CitationChip n={1} />;`)).toEqual(['kit:CitationChip']);
  });

  it('raw button fails, in a Tooltip or with data-tip-id passes', () => {
    expect(scan(`export const A = () => <button>Foo</button>;`)).toEqual(['raw:button']);
    expect(scan(`export const A = () => <Tooltip tip="x"><button>Foo</button></Tooltip>;`)).toEqual([]);
    expect(scan(`export const A = () => <button data-tip-id="x">Foo</button>;`)).toEqual([]);
  });

  it('a Tooltip far above does not cover a nested control', () => {
    expect(scan(`export const A = () => <Tooltip tip="x"><div><button>Foo</button></div></Tooltip>;`)).toEqual(['raw:button']);
  });

  it('raw link, anchor fail', () => {
    expect(scan(`export const A = () => <Link href="/">Foo</Link>;`)).toEqual(['raw:Link']);
    expect(scan(`export const A = () => <a href="/">Foo</a>;`)).toEqual(['raw:a']);
  });

  it('role radio, option, tab, button fail', () => {
    expect(scan(`export const A = () => <div role="radio" />;`)).toEqual(['raw:div[role=radio]']);
    expect(scan(`export const A = () => <li role="option" />;`)).toEqual(['raw:li[role=option]']);
    expect(scan(`export const A = () => <div role="tab" />;`)).toEqual(['raw:div[role=tab]']);
    expect(scan(`export const A = () => <span role="button" />;`)).toEqual(['raw:span[role=button]']);
  });

  it('input radio and checkbox fail, text input passes', () => {
    expect(scan(`export const A = () => <input type="radio" />;`)).toEqual(['raw:input']);
    expect(scan(`export const A = () => <input type="checkbox" />;`)).toEqual(['raw:input']);
    expect(scan(`export const A = () => <input type="text" />;`)).toEqual([]);
  });

  it('tip={NO_TIP} needs an adjacent comment', () => {
    expect(scan(`export const A = () => <Button tip={NO_TIP}>x</Button>;`)).toEqual(['no-tip:Button']);
    expect(scan(`export const A = () => (\n  // decorative: the label says it all\n  <Button tip={NO_TIP}>x</Button>\n);`)).toEqual([]);
    expect(scan(`export const A = () => <Button tip={NO_TIP /* label is the tip */}>x</Button>;`)).toEqual([]);
  });

  it('a compliant fixture passes', () => {
    expect(
      scan(`export const A = () => (
        <div>
          <Button tip="why.edit">Edit</Button>
          <LinkButton href="/" tip={{ purpose: 'a', effect: 'b' }}>Go</LinkButton>
          <Chip tip="explore.link" href="/x">Y</Chip>
          <CitationChip n={1} tip="explore.link" />
          <Tooltip tip="x"><Link href="/">Z</Link></Tooltip>
        </div>
      );`),
    ).toEqual([]);
  });

  it('keys are stable ordinals per file, rule and tag', () => {
    const keys = scanSource('f.tsx', `export const A = () => <div><button/><button/></div>;`).map((g) => g.key);
    expect(keys).toEqual(['f.tsx|raw|button|1', 'f.tsx|raw|button|2']);
  });
});
