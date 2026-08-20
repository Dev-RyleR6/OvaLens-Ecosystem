import React, { useState, useEffect } from 'react';
import {
  Settings,
  Save,
  CheckCircle2,
  Building,
  Cpu,
  Coins,
  ShieldCheck,
  RotateCcw,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { HatcherySettings } from '../types';

export const SettingsPage: React.FC = () => {
  const [settings, setSettings] = useState<HatcherySettings | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    const fetchSettings = async () => {
      const data = await apiClient.getSettings();
      setSettings({ ...data });
    };
    fetchSettings();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!settings) return;

    setIsSaving(true);
    try {
      await apiClient.updateSettings(settings);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } finally {
      setIsSaving(false);
    }
  };

  if (!settings) return null;

  return (
    <div className="space-y-6 pb-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-[#0F172A] tracking-tight">
            Hatchery Facility & AI Configuration
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Foundation University institutional settings, candling vision thresholds, and market prices.
          </p>
        </div>

        <button
          onClick={handleSave}
          disabled={isSaving}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#800000] hover:bg-[#6B0000] text-white text-xs font-bold shadow-xs transition-colors cursor-pointer disabled:opacity-50"
        >
          <Save className="w-4 h-4" />
          <span>{isSaving ? 'Saving Changes...' : 'Save Configuration'}</span>
        </button>
      </div>

      {saveSuccess && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs font-semibold text-emerald-800 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-700" />
          <span>Configuration saved and propagated to Edge Stations.</span>
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* Section 1: Institutional & Facility Profile */}
        <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-xs space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <Building className="w-4 h-4 text-[#800000]" />
            <h3 className="text-sm font-bold text-[#0F172A]">
              Facility & Institutional Profile
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="space-y-1.5">
              <label className="font-semibold text-slate-700">Hatchery Facility Name</label>
              <input
                type="text"
                value={settings.facility_name}
                onChange={(e) => setSettings({ ...settings, facility_name: e.target.value })}
                className="w-full h-9 px-3 bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000]"
              />
            </div>

            <div className="space-y-1.5">
              <label className="font-semibold text-slate-700">Parent University / Institution</label>
              <input
                type="text"
                value={settings.institution}
                onChange={(e) => setSettings({ ...settings, institution: e.target.value })}
                className="w-full h-9 px-3 bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000]"
              />
            </div>

            <div className="space-y-1.5 md:col-span-2">
              <label className="font-semibold text-slate-700">Physical Location</label>
              <input
                type="text"
                value={settings.location}
                onChange={(e) => setSettings({ ...settings, location: e.target.value })}
                className="w-full h-9 px-3 bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000]"
              />
            </div>
          </div>
        </div>

        {/* Section 2: AI Candling & Vision Thresholds */}
        <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-xs space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <Cpu className="w-4 h-4 text-[#800000]" />
            <h3 className="text-sm font-bold text-[#0F172A]">
              Optical Candling & AI Inference Thresholds
            </h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
            <div className="space-y-1.5 p-3 bg-slate-50 rounded-lg border border-slate-200">
              <div className="flex justify-between font-semibold text-slate-700">
                <span>Minimum Confidence:</span>
                <span className="font-bold text-[#800000]">{(settings.min_confidence_threshold * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0.30"
                max="0.90"
                step="0.05"
                value={settings.min_confidence_threshold}
                onChange={(e) => setSettings({ ...settings, min_confidence_threshold: Number(e.target.value) })}
                className="w-full accent-[#800000] cursor-pointer"
              />
              <span className="text-[11px] text-slate-500 block">YOLOv8 FP16 detection filter threshold</span>
            </div>

            <div className="space-y-1.5 p-3 bg-slate-50 rounded-lg border border-slate-200">
              <div className="flex justify-between font-semibold text-slate-700">
                <span>Min Aspect Ratio:</span>
                <span className="font-bold text-slate-900">{settings.aspect_ratio_min}</span>
              </div>
              <input
                type="range"
                min="0.50"
                max="0.80"
                step="0.05"
                value={settings.aspect_ratio_min}
                onChange={(e) => setSettings({ ...settings, aspect_ratio_min: Number(e.target.value) })}
                className="w-full accent-[#800000] cursor-pointer"
              />
              <span className="text-[11px] text-slate-500 block">Duck egg geometric ovality lower bound</span>
            </div>

            <div className="space-y-1.5 p-3 bg-slate-50 rounded-lg border border-slate-200">
              <div className="flex justify-between font-semibold text-slate-700">
                <span>Max Aspect Ratio:</span>
                <span className="font-bold text-slate-900">{settings.aspect_ratio_max}</span>
              </div>
              <input
                type="range"
                min="1.10"
                max="1.80"
                step="0.05"
                value={settings.aspect_ratio_max}
                onChange={(e) => setSettings({ ...settings, aspect_ratio_max: Number(e.target.value) })}
                className="w-full accent-[#800000] cursor-pointer"
              />
              <span className="text-[11px] text-slate-500 block">Duck egg geometric ovality upper bound</span>
            </div>
          </div>
        </div>

        {/* Section 3: Commercial Economic Unit Prices */}
        <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-xs space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <Coins className="w-4 h-4 text-[#800000]" />
            <h3 className="text-sm font-bold text-[#0F172A]">
              Commercial Valuation & Economic Rates
            </h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
            <div className="space-y-1.5">
              <label className="font-semibold text-slate-700">Day 10 Penoy Salvage (₱ / egg)</label>
              <input
                type="number"
                step="0.50"
                value={settings.penoy_unit_price}
                onChange={(e) => setSettings({ ...settings, penoy_unit_price: Number(e.target.value) })}
                className="w-full h-9 px-3 bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000]"
              />
            </div>

            <div className="space-y-1.5">
              <label className="font-semibold text-slate-700">Day-Old Duckling Selling Price (₱)</label>
              <input
                type="number"
                step="1.00"
                value={settings.duckling_unit_price}
                onChange={(e) => setSettings({ ...settings, duckling_unit_price: Number(e.target.value) })}
                className="w-full h-9 px-3 bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000]"
              />
            </div>

            <div className="space-y-1.5">
              <label className="font-semibold text-slate-700">Electricity Utility Tariff (₱ / kWh)</label>
              <input
                type="number"
                step="0.25"
                value={settings.kwh_rate_php}
                onChange={(e) => setSettings({ ...settings, kwh_rate_php: Number(e.target.value) })}
                className="w-full h-9 px-3 bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000]"
              />
            </div>
          </div>
        </div>
      </form>
    </div>
  );
};
