import { useEffect, useRef } from 'react';

const focusableSelector = 'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
const stack: HTMLElement[] = [];
let previousOverflow = '';

/** Keep nested overlays keyboard-contained and restore the caller's focus. */
export function useDialogAccessibility(open: boolean, onClose: () => void, label: string) {
  const ref = useRef<HTMLDivElement>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    const dialog = ref.current;
    if (!open || !dialog) return;
    const previous = document.activeElement as HTMLElement | null;
    if (stack.length === 0) previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    stack.push(dialog);
    dialog.setAttribute('role', 'dialog');
    dialog.setAttribute('aria-modal', 'true');
    dialog.setAttribute('aria-label', label);
    dialog.tabIndex = -1;
    const focusables = () => Array.from(dialog.querySelectorAll<HTMLElement>(focusableSelector))
      .filter(element => element.getClientRects().length > 0 && !element.closest('[inert]'));
    (focusables()[0] || dialog).focus();
    const keydown = (event: KeyboardEvent) => {
      if (stack[stack.length - 1] !== dialog) return;
      if (event.key === 'Escape') {
        event.preventDefault();
        event.stopImmediatePropagation();
        closeRef.current();
      }
      if (event.key === 'Tab') {
        const elements = focusables();
        const first = elements[0] || dialog;
        const last = elements[elements.length - 1] || dialog;
        if (!elements.length || !dialog.contains(document.activeElement) ||
            (event.shiftKey && document.activeElement === first) ||
            (!event.shiftKey && document.activeElement === last)) {
          event.preventDefault();
          (event.shiftKey ? last : first).focus();
        }
      }
    };
    const containFocus = (event: FocusEvent) => {
      if (stack[stack.length - 1] === dialog && !dialog.contains(event.target as Node)) {
        (focusables()[0] || dialog).focus();
      }
    };
    document.addEventListener('keydown', keydown, true);
    document.addEventListener('focusin', containFocus);
    return () => {
      stack.splice(stack.indexOf(dialog), 1);
      dialog.removeAttribute('aria-modal');
      dialog.removeAttribute('role');
      dialog.removeAttribute('aria-label');
      dialog.removeAttribute('tabindex');
      if (stack.length === 0) document.body.style.overflow = previousOverflow;
      document.removeEventListener('keydown', keydown, true);
      document.removeEventListener('focusin', containFocus);
      if (previous?.isConnected) previous.focus();
    };
  }, [open, label]);
  return ref;
}
