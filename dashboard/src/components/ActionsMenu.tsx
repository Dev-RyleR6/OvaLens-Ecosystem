import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { ChevronDown } from 'lucide-react';

interface MenuAction {
  label: string;
  icon?: ReactNode;
  destructive?: boolean;
  onSelect: () => void;
}

/** Portaled so table scrolling and clipping never change the menu or row size. */
export function ActionsMenu({ label, actions }: { label: string; actions: MenuAction[] }) {
  const id = useId();
  const trigger = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0 });
  const close = (restoreFocus = false) => {
    setOpen(false);
    if (restoreFocus) trigger.current?.focus({ preventScroll: true });
  };

  useLayoutEffect(() => {
    if (!open || !trigger.current || !menu.current) return;
    const anchor = trigger.current.getBoundingClientRect();
    const panel = menu.current.getBoundingClientRect();
    setPosition({
      left: Math.max(8, Math.min(anchor.right - panel.width, window.innerWidth - panel.width - 8)),
      top: anchor.bottom + panel.height + 8 <= window.innerHeight
        ? anchor.bottom + 6 : Math.max(8, anchor.top - panel.height - 6),
    });
    menu.current.querySelector<HTMLButtonElement>('button')?.focus({ preventScroll: true });
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const outside = (event: PointerEvent) => {
      const target = event.target as Node;
      if (!menu.current?.contains(target) && !trigger.current?.contains(target)) setOpen(false);
    };
    const reposition = (event: Event) => {
      if (event.type === 'resize' || !menu.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener('pointerdown', outside);
    window.addEventListener('resize', reposition);
    document.addEventListener('scroll', reposition, true);
    return () => {
      document.removeEventListener('pointerdown', outside);
      window.removeEventListener('resize', reposition);
      document.removeEventListener('scroll', reposition, true);
    };
  }, [open]);

  return <>
    <button ref={trigger} className="secondary-action" aria-label={label} aria-haspopup="menu" aria-expanded={open} aria-controls={open ? id : undefined}
      onClick={() => setOpen(value => !value)} onKeyDown={event => {
        if (event.key === 'ArrowDown' || event.key === 'ArrowUp') { event.preventDefault(); setOpen(true); }
      }}>
      More<ChevronDown aria-hidden="true" className="w-4 h-4" />
    </button>
    {open && createPortal(<div ref={menu} id={id} role="menu" aria-label={label} className="actions-menu" style={position}
      onBlur={event => { if (event.relatedTarget !== trigger.current && !event.currentTarget.contains(event.relatedTarget as Node | null)) setOpen(false); }}
      onKeyDown={event => {
        if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); close(true); }
        if (event.key === 'Tab') close(true);
        if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
          event.preventDefault();
          const buttons = Array.from(menu.current?.querySelectorAll<HTMLButtonElement>('button') ?? []);
          const current = buttons.indexOf(document.activeElement as HTMLButtonElement);
          const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1
            : (current + (event.key === 'ArrowDown' ? 1 : -1) + buttons.length) % buttons.length;
          buttons[next]?.focus();
        }
      }}>
      {actions.map(action => <button key={action.label} role="menuitem" className={action.destructive ? 'actions-menu-danger' : ''}
        onClick={() => { close(true); action.onSelect(); }}>{action.icon}{action.label}</button>)}
    </div>, document.body)}
  </>;
}
