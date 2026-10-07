export interface Preferences {
  pollingInterval: number;
  tableDensity: 'compact' | 'comfortable';
  theme: 'light' | 'dark';
}

export function readPreferences(): Preferences {
  const saved = localStorage.getItem('ovalens_polling_interval');
  const interval = saved === null ? 10 : Number(saved);
  return {
    pollingInterval: [0, 5, 10, 30].includes(interval) ? interval : 10,
    tableDensity: localStorage.getItem('ovalens_table_density') === 'compact' ? 'compact' : 'comfortable',
    theme: localStorage.getItem('ovalens_theme') === 'dark' ? 'dark' : 'light',
  };
}

export function savePreferences(preferences: Preferences) {
  localStorage.setItem('ovalens_polling_interval', String(preferences.pollingInterval));
  localStorage.setItem('ovalens_table_density', preferences.tableDensity);
  localStorage.setItem('ovalens_theme', preferences.theme);
  window.dispatchEvent(new Event('ovalens-preferences'));
}
