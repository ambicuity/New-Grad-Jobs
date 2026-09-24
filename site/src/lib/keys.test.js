// @vitest-environment jsdom
import { afterEach, describe, expect, it } from 'vitest';
import { isEditableTarget, shouldIgnoreShortcut } from './keys.js';

const mount = (html) => {
  document.body.innerHTML = html;
  return (sel) => document.querySelector(sel);
};
const ev = (target, mods = {}) => ({ target, ctrlKey: false, metaKey: false, altKey: false, ...mods });

afterEach(() => { document.body.innerHTML = ''; });

describe('isEditableTarget', () => {
  it('is true for text fields, selects and contenteditable', () => {
    const $ = mount(`
      <input id="i"><textarea id="t"></textarea><select id="s"></select>
      <div contenteditable="true"><span id="ce">x</span></div>
      <div id="plain"></div>`);
    expect(isEditableTarget($('#i'))).toBe(true);
    expect(isEditableTarget($('#t'))).toBe(true);
    expect(isEditableTarget($('#s'))).toBe(true);
    expect(isEditableTarget($('#ce'))).toBe(true);
    expect(isEditableTarget($('#plain'))).toBe(false);
    expect(isEditableTarget(null)).toBe(false);
    expect(isEditableTarget(window)).toBe(false);
  });
});

describe('shouldIgnoreShortcut', () => {
  const $ = () => mount(`
    <input id="search">
    <button id="btn"><span id="inbtn">x</span></button>
    <a id="link" href="#x">x</a>
    <div id="rb" role="button" tabindex="0"></div>
    <div id="list" role="listbox" tabindex="0"><div id="opt" role="option">row</div></div>
    <div id="plain"></div>`);

  it('ignores keys typed into editable fields', () => {
    expect(shouldIgnoreShortcut(ev($()('#search')))).toBe(true);
  });

  it('ignores keys while a button, link or role=button has focus', () => {
    const q = $();
    expect(shouldIgnoreShortcut(ev(q('#btn')))).toBe(true);
    expect(shouldIgnoreShortcut(ev(q('#inbtn')))).toBe(true);
    expect(shouldIgnoreShortcut(ev(q('#link')))).toBe(true);
    expect(shouldIgnoreShortcut(ev(q('#rb')))).toBe(true);
    expect(shouldIgnoreShortcut(ev(q('#opt')))).toBe(true);
  });

  it('handles keys on the job listbox itself and on plain page content', () => {
    const q = $();
    expect(shouldIgnoreShortcut(ev(q('#list')))).toBe(false);
    expect(shouldIgnoreShortcut(ev(q('#plain')))).toBe(false);
    expect(shouldIgnoreShortcut(ev(document.body))).toBe(false);
    expect(shouldIgnoreShortcut(ev(window))).toBe(false);
  });

  it.each(['ctrlKey', 'metaKey', 'altKey'])('ignores any key combined with %s', (mod) => {
    expect(shouldIgnoreShortcut(ev(document.body, { [mod]: true }))).toBe(true);
  });
});
