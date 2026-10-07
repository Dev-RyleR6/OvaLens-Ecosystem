import { useEffect, useState } from 'react';
import { readPreferences } from '../lib/preferences';
export { readPreferences, savePreferences } from '../lib/preferences';

export function usePreferences() {
  const [preferences, setPreferences] = useState(readPreferences);
  useEffect(() => {
    const update = () => setPreferences(readPreferences());
    window.addEventListener('storage', update);
    window.addEventListener('ovalens-preferences', update);
    return () => {
      window.removeEventListener('storage', update);
      window.removeEventListener('ovalens-preferences', update);
    };
  }, []);
  return preferences;
}
