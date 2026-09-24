// When global single-key shortcuts (j/k, s, /, ?) must stand aside.

const EDITABLE = 'input, textarea, select, [contenteditable=""], [contenteditable="true"]';
// Focus on these means Enter/Space/letters belong to that control, not to us.
const INTERACTIVE = 'button, a[href], summary, [role="button"], [role="link"], [role="option"], [role="tab"], [role="menuitem"], [role="checkbox"], [role="switch"]';
// The job list is a listbox that owns its keyboard handling via these shortcuts.
const OWN_LIST = '[role="listbox"]';

const isElement = (el) => !!el && typeof el.closest === 'function';

/** True when `el` is (inside) a text field, select or contenteditable region. */
export function isEditableTarget(el) {
  if (!isElement(el)) return false;
  return el.isContentEditable === true || el.closest(EDITABLE) !== null;
}

/**
 * @param {{target: EventTarget|null, ctrlKey: boolean, metaKey: boolean, altKey: boolean}} e
 * @returns {boolean} true when a global shortcut must not handle this keydown
 */
export function shouldIgnoreShortcut(e) {
  if (e.ctrlKey || e.metaKey || e.altKey) return true;
  const el = e.target;
  if (!isElement(el)) return false;
  if (isEditableTarget(el)) return true;
  if (el.matches(OWN_LIST)) return false;
  return el.closest(INTERACTIVE) !== null;
}
