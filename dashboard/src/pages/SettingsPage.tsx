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
  Zap,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { DataUnavailableState } from '../components/ui/DataUnavailableState';

export const SettingsPage: React.FC = () => {
  const [facilityName, setFacilityName] = useState('Foundation University Automated Hatchery');
  const [institution, setInstitution] = useState('Foundation University - Dumaguete City');
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.85);
  const [penoyPrice, setPenoyPrice] = useState(14.00);
  const [ducklingPrice, setDucklingPrice] = useState(40.00);
  const [kwhRate, setKwhRate] = useState(12.50);
  const [kwhSavedPerEgg, setKwhSavedPerEgg] = useState(0.20);
  const [conveyorSpeed, setConveyorSpeed] = useState(10.0);
  const [conveyorDistance, setConveyorDistance] = useState(25.0);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isError, setIsError] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const fetchSettings = async () => {
    setIsLoading(true);
    setIsError(false);
    try {
      const data = await apiClient.getSettings();
      if (data) {
        if (data.facility_name) setFacilityName(data.facility_name);
        if (data.institution) setInstitution(data.institution);
        if (data.confidence_threshold !== undefined) setConfidenceThreshold(data.confidence_threshold);
        if (data.penoy_unit_price_php !== undefined) setPenoyPrice(data.penoy_unit_price_php);
        else if (data.penoy_unit_price !== undefined) setPenoyPrice(data.penoy_unit_price);
        if (data.duckling_unit_price_php !== undefined) setDucklingPrice(data.duckling_unit_price_php);
        else if (data.duckling_unit_price !== undefined) setDucklingPrice(data.duckling_unit_price);
        if (data.electricity_kwh_rate_php !== undefined) setKwhRate(data.electricity_kwh_rate_php);
        else if (data.kwh_rate_php !== undefined) setKwhRate(data.kwh_rate_php);
        if (data.kwh_saved_per_culled_egg !== undefined) setKwhSavedPerEgg(data.kwh_saved_per_culled_egg);
        if (data.conveyor_speed_cm_s !== undefined) setConveyorSpeed(data.conveyor_speed_cm_s);
        if (data.conveyor_distance_cm !== undefined) setConveyorDistance(data.conveyor_distance_cm);
      }
    } catch (err) {
      console.error('Failed to load settings:', err);
      setIsError(true);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      await apiClient.updateSettings({
        facility_name: facilityName,
        institution,
        confidence_threshold: confidenceThreshold,
        penoy_unit_price_php: penoyPrice,
        duckling_unit_price_php: ducklingPrice,
        electricity_kwh_rate_php: kwhRate,
        kwh_saved_per_culled_egg: kwhSavedPerEgg,
        conveyor_speed_cm_s: conveyorSpeed,
        conveyor_distance_cm: conveyorDistance,
      });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3500);
    } finally {
      setIsSaving(false);
    }
  };

  if (isError && !facilityName) {
    return (
      <div className="space-y-6 max-w-4xl pb-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200">
          <div>
            <h1 className="text-xl font-bold text-[#0F172A] tracking-tight">
              Hatchery Facility Settings
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              System-wide economic valuation constants, optical confidence thresholds, and hardware timing parameters.
            </p>
          </div>
        </div>
        <DataUnavailableState
          title="Facility Settings Offline"
          description="Unable to load persistent settings from the PostgreSQL database. Ensure the backend REST service is reachable."
          onRetry={fetchSettings}
          isRetrying={isLoading}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl pb-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-[#0F172A] tracking-tight">
            Hatchery Facility Settings
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            System-wide economic valuation constants, optical confidence thresholds, and hardware timing parameters.
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
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs font-semibold text-emerald-800 flex items-center gap-2 animate-in fade-in">
          <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0" />
          <span>Configuration saved and live economic calculations updated!</span>
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
                value={facilityName}
                onChange={(e) => setFacilityName(e.target.value)}
                className="w-full h-9 px-3 bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000]"
              />
            </div>

            <div className="space-y-1.5">
              <label className="font-semibold text-slate-700">Parent University / Institution</label>
              <input
                type="text"
                value={institution}
                onChange={(e) => setInstitution(e.target.value)}
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
              Optical Candling & Sorter Kinematics
            </h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
            <div className="space-y-1.5 p-3 bg-slate-50 rounded-lg border border-slate-200">
              <div className="flex justify-between font-semibold text-slate-700">
                <span>Minimum Confidence:</span>
                <span className="font-bold text-[#800000]">{(confidenceThreshold * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0.30"
                max="0.95"
                step="0.05"
                value={confidenceThreshold}
                onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
                className="w-full accent-[#800000] cursor-pointer"
              />
              <span className="text-[11px] text-slate-500 block">YOLOv8 FP16 detection filter threshold</span>
            </div>

            <div className="space-y-1.5 p-3 bg-slate-50 rounded-lg border border-slate-200">
              <div className="flex justify-between font-semibold text-slate-700">
                <span>Conveyor Speed (cm/s):</span>
                <span className="font-bold text-slate-900">{conveyorSpeed} cm/s</span>
              </div>
              <input
                type="number"
                step="0.5"
                min="1"
                max="50"
                value={conveyorSpeed}
                onChange={(e) => setConveyorSpeed(Number(e.target.value))}
                className="w-full h-8 px-2 bg-white border border-slate-200 rounded text-slate-800 focus:outline-none focus:border-[#800000]"
              />
              <span className="text-[11px] text-slate-500 block">Belt linear velocity ($v$)</span>
            </div>

            <div className="space-y-1.5 p-3 bg-slate-50 rounded-lg border border-slate-200">
              <div className="flex justify-between font-semibold text-slate-700">
                <span>Sensor Distance (cm):</span>
                <span className="font-bold text-slate-900">{conveyorDistance} cm</span>
              </div>
              <input
                type="number"
                step="0.5"
                min="1"
                max="100"
                value={conveyorDistance}
                onChange={(e) => setConveyorDistance(Number(e.target.value))}
                className="w-full h-8 px-2 bg-white border border-slate-200 rounded text-slate-800 focus:outline-none focus:border-[#800000]"
              />
              <span className="text-[11px] text-slate-500 block">Distance to diverter servo ($D$)</span>
            </div>
          </div>
        </div>

        {/* Section 3: Commercial Economic Unit Prices */}
        <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-xs space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <Coins className="w-4 h-4 text-[#800000]" />
            <h3 className="text-sm font-bold text-[#0F172A]">
              Commercial Valuation & Economic Market Rates
            </h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-xs">
            <div className="space-y-1.5">
              <label className="font-semibold text-slate-700">Day 10 Penoy Salvage (₱ / egg)</label>
              <input
                type="number"
                step="0.50"
                value={penoyPrice}
                onChange={(e) => setPenoyPrice(Number(e.target.value))}
                className="w-full h-9 px-3 bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000]"
              />
            </div>

            <div className="space-y-1.5">
              <label className="font-semibold text-slate-700">Duckling Selling Price (₱ / bird)</label>
              <input
                type="number"
                step="1.00"
                value={ducklingPrice}
                onChange={(e) => setDucklingPrice(Number(e.target.value))}
                className="w-full h-9 px-3 bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000]"
              />
            </div>

            <div className="space-y-1.5">
              <label className="font-semibold text-slate-700">Electricity Utility Tariff (₱ / kWh)</label>
              <input
                type="number"
                step="0.25"
                value={kwhRate}
                onChange={(e) => setKwhRate(Number(e.target.value))}
                className="w-full h-9 px-3 bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000]"
              />
            </div>

            <div className="space-y-1.5">
              <label className="font-semibold text-slate-700">kWh Saved / Culled Egg</label>
              <input
                type="number"
                step="0.01"
                value={kwhSavedPerEgg}
                onChange={(e) => setKwhSavedPerEgg(Number(e.target.value))}
                className="w-full h-9 px-3 bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000]"
              />
            </div>
          </div>
        </div>
      </form>
    </div>
  );
};
