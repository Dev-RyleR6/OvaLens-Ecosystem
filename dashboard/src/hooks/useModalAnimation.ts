import { useState, useEffect } from 'react';

/**
 * useModalAnimation
 * Manages smooth mounting and exit animation delays for modals and slide-out sheets.
 */
export function useModalAnimation(isOpen: boolean, duration: number = 200) {
  const [shouldRender, setShouldRender] = useState(isOpen);
  const [isClosing, setIsClosing] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setShouldRender(true);
      setIsClosing(false);
    } else if (shouldRender) {
      setIsClosing(true);
      const timer = setTimeout(() => {
        setShouldRender(false);
        setIsClosing(false);
      }, duration);
      return () => clearTimeout(timer);
    }
  }, [isOpen, duration, shouldRender]);

  return { shouldRender, isClosing };
}
