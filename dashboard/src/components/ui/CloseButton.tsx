import type { ButtonHTMLAttributes } from 'react';
import { X } from 'lucide-react';

export function CloseButton({ className = '', 'aria-label': label = 'Close dialog', ...props }: Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'>) {
  return <button {...props} type="button" aria-label={label} className={`close-button ${className}`}>
    <X aria-hidden="true" size={18} strokeWidth={1.75} />
  </button>;
}
