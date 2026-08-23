import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Building,
  Coins,
  Zap,
  Save,
  CheckCircle2,
  AlertTriangle,
  User as UserIcon,
  Key,
  HardDrive,
  Download,
  Sliders,
  Database,
  RefreshCw,
  Eye,
  EyeOff,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { DataUnavailableState } from '../components/ui/DataUnavailableState';
import { ConfirmationModal } from '../components/ui/ConfirmationModal';

type SettingsTab = 'facility' | 'account' | 'backups' | 'preferences';

interface BackupArchive {
  filename: string;
  file_size_kb: number;
  created_at: string;
}

export const SettingsPage: React.FC = () => {
  const { user, updateUser } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get('tab') as SettingsTab | null;

  const [activeTab, setActiveTab] = useState<SettingsTab>(() => {
    if (tabParam && ['facility', 'account', 'backups', 'preferences'].includes(tabParam)) {
      return tabParam;
    }
    return 'facility';
  });

  useEffect(() => {
    if (tabParam && ['facility', 'account', 'backups', 'preferences'].includes(tabParam)) {
      setActiveTab(tabParam);
    }
  }, [tabParam]);

  const handleTabChange = (tab: SettingsTab) => {
    setActiveTab(tab);
    setSearchParams({ tab });
  };

  // --- Facility Settings State ---
  const [facilityName, setFacilityName] = useState('Foundation University Automated Hatchery');
  const [institution, setInstitution] = useState('Foundation University - Dumaguete City');
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.85);
  const [penoyPrice, setPenoyPrice] = useState(14.00);
  const [ducklingPrice, setDucklingPrice] = useState(40.00);
  const [kwhRate, setKwhRate] = useState(12.50);
  const [kwhSavedPerEgg, setKwhSavedPerEgg] = useState(0.20);
  const [conveyorSpeed, setConveyorSpeed] = useState(10.0);
  const [conveyorDistance, setConveyorDistance] = useState(25.0);

  const [originalFacility, setOriginalFacility] = useState<any>(null);
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isError, setIsError] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // --- Account & Profile State ---
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [profileSuccess, setProfileSuccess] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);

  // Password Change State
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  // --- Backups State ---
  const [backups, setBackups] = useState<BackupArchive[]>([]);
  const [isLoadingBackups, setIsLoadingBackups] = useState(false);
  const [isCreatingBackup, setIsCreatingBackup] = useState(false);
  const [backupSuccess, setBackupSuccess] = useState(false);

  // --- Preferences State ---
  const [pollingInterval, setPollingInterval] = useState<number>(() => {
    return Number(localStorage.getItem('ovalens_polling_interval')) || 10;
  });
  const [audioAlerts, setAudioAlerts] = useState<boolean>(() => {
    return localStorage.getItem('ovalens_audio_alerts') !== 'false';
  });
  const [tableDensity, setTableDensity] = useState<'compact' | 'comfortable'>(() => {
    return (localStorage.getItem('ovalens_table_density') as 'compact' | 'comfortable') || 'comfortable';
  });
  const [prefSaved, setPrefSaved] = useState(false);

  useEffect(() => {
    if (user?.full_name) {
      setFullName(user.full_name);
    }
  }, [user]);

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

        setOriginalFacility({
          facility_name: data.facility_name || 'Foundation University Automated Hatchery',
          institution: data.institution || 'Foundation University - Dumaguete City',
          confidence_threshold: data.confidence_threshold ?? 0.85,
          penoy_unit_price_php: data.penoy_unit_price_php ?? data.penoy_unit_price ?? 14.00,
          duckling_unit_price_php: data.duckling_unit_price_php ?? data.duckling_unit_price ?? 40.00,
          electricity_kwh_rate_php: data.electricity_kwh_rate_php ?? data.kwh_rate_php ?? 12.50,
          kwh_saved_per_culled_egg: data.kwh_saved_per_culled_egg ?? 0.20,
          conveyor_speed_cm_s: data.conveyor_speed_cm_s ?? 10.0,
          conveyor_distance_cm: data.conveyor_distance_cm ?? 25.0,
        });
      }
    } catch (err) {
      console.error('Failed to load settings:', err);
      setIsError(true);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchBackupsList = async () => {
    setIsLoadingBackups(true);
    try {
      const data = await apiClient.getBackups();
      if (Array.isArray(data)) {
        setBackups(data);
      }
    } catch (err) {
      console.error('Failed to load backups:', err);
    } finally {
      setIsLoadingBackups(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  useEffect(() => {
    if (activeTab === 'backups') {
      fetchBackupsList();
    }
  }, [activeTab]);

  const calculateDiffs = () => {
    if (!originalFacility) return [];
    const diffs = [];
    if (originalFacility.penoy_unit_price_php !== penoyPrice) {
      diffs.push({ label: 'Penoy Selling Price', oldValue: `₱${Number(originalFacility.penoy_unit_price_php).toFixed(2)}`, newValue: `₱${Number(penoyPrice).toFixed(2)}` });
    }
    if (originalFacility.duckling_unit_price_php !== ducklingPrice) {
      diffs.push({ label: 'Duckling Selling Price', oldValue: `₱${Number(originalFacility.duckling_unit_price_php).toFixed(2)}`, newValue: `₱${Number(ducklingPrice).toFixed(2)}` });
    }
    if (originalFacility.electricity_kwh_rate_php !== kwhRate) {
      diffs.push({ label: 'Electricity Rate', oldValue: `₱${Number(originalFacility.electricity_kwh_rate_php).toFixed(2)}/kWh`, newValue: `₱${Number(kwhRate).toFixed(2)}/kWh` });
    }
    if (originalFacility.confidence_threshold !== confidenceThreshold) {
      diffs.push({ label: 'AI Confidence Threshold', oldValue: `${Number(originalFacility.confidence_threshold * 100).toFixed(0)}%`, newValue: `${Number(confidenceThreshold * 100).toFixed(0)}%` });
    }
    if (originalFacility.facility_name !== facilityName) {
      diffs.push({ label: 'Facility Name', oldValue: originalFacility.facility_name, newValue: facilityName });
    }
    if (originalFacility.institution !== institution) {
      diffs.push({ label: 'Institution Affiliation', oldValue: originalFacility.institution, newValue: institution });
    }
    if (originalFacility.conveyor_speed_cm_s !== conveyorSpeed) {
      diffs.push({ label: 'Conveyor Belt Speed', oldValue: `${originalFacility.conveyor_speed_cm_s} cm/s`, newValue: `${conveyorSpeed} cm/s` });
    }
    return diffs;
  };

  const handleExecuteSaveFacility = async () => {
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
      setOriginalFacility({
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
      setIsConfirmOpen(false);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3500);
    } catch (err) {
      console.error('Failed to save settings:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullName.trim()) {
      setProfileError('Full name cannot be empty.');
      return;
    }
    setIsSavingProfile(true);
    setProfileError(null);
    try {
      const updated = await apiClient.updateMyProfile(fullName.trim());
      updateUser(updated);
      setProfileSuccess(true);
      setTimeout(() => setProfileSuccess(false), 3500);
    } catch (err: any) {
      setProfileError(err?.response?.data?.detail || 'Failed to update profile name.');
    } finally {
      setIsSavingProfile(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError(null);

    if (!currentPassword) {
      setPasswordError('Please enter your current password.');
      return;
    }
    if (newPassword.length < 6) {
      setPasswordError('New password must be at least 6 characters.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError('New passwords do not match.');
      return;
    }

    setIsChangingPassword(true);
    try {
      await apiClient.changeMyPassword(currentPassword, newPassword);
      setPasswordSuccess(true);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setTimeout(() => setPasswordSuccess(false), 4000);
    } catch (err: any) {
      setPasswordError(err?.response?.data?.detail || 'Password update failed. Verify your current password.');
    } finally {
      setIsChangingPassword(false);
    }
  };

  const handleCreateBackup = async () => {
    setIsCreatingBackup(true);
    try {
      await apiClient.createBackup();
      setBackupSuccess(true);
      await fetchBackupsList();
      setTimeout(() => setBackupSuccess(false), 4000);
    } catch (err) {
      console.error('Failed to create database snapshot:', err);
    } finally {
      setIsCreatingBackup(false);
    }
  };

  const handleSavePreferences = (e: React.FormEvent) => {
    e.preventDefault();
    localStorage.setItem('ovalens_polling_interval', String(pollingInterval));
    localStorage.setItem('ovalens_audio_alerts', String(audioAlerts));
    localStorage.setItem('ovalens_table_density', tableDensity);
    setPrefSaved(true);
    setTimeout(() => setPrefSaved(false), 3000);
  };

  if (isError && !facilityName) {
    return (
      <div className="space-y-6 max-w-4xl pb-8">
        <div className="pb-4 border-b border-slate-200">
          <h1 className="text-xl font-bold text-[#0F172A] tracking-tight">
            Settings & System Preferences
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Facility constants, user profile security, automated backups, and display preferences.
          </p>
        </div>
        <DataUnavailableState
          title="Settings Service Offline"
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
            Settings & System Preferences
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Manage institutional constants, your user credentials, database backup archives, and UI alerts.
          </p>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex border-b border-slate-200 gap-1 sm:gap-2">
        <button
          onClick={() => handleTabChange('facility')}
          className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-semibold rounded-t-lg transition-colors border-b-2 ${
            activeTab === 'facility'
              ? 'border-[#800000] text-[#800000] bg-red-50/50'
              : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-50'
          }`}
        >
          <Building className="w-4 h-4" />
          <span>Facility & Economics</span>
        </button>

        <button
          onClick={() => handleTabChange('account')}
          className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-semibold rounded-t-lg transition-colors border-b-2 ${
            activeTab === 'account'
              ? 'border-[#800000] text-[#800000] bg-red-50/50'
              : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-50'
          }`}
        >
          <UserIcon className="w-4 h-4" />
          <span>My Profile & Password</span>
        </button>

        <button
          onClick={() => handleTabChange('backups')}
          className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-semibold rounded-t-lg transition-colors border-b-2 ${
            activeTab === 'backups'
              ? 'border-[#800000] text-[#800000] bg-red-50/50'
              : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-50'
          }`}
        >
          <HardDrive className="w-4 h-4" />
          <span>Database Backups</span>
        </button>

        <button
          onClick={() => handleTabChange('preferences')}
          className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-semibold rounded-t-lg transition-colors border-b-2 ${
            activeTab === 'preferences'
              ? 'border-[#800000] text-[#800000] bg-red-50/50'
              : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-50'
          }`}
        >
          <Sliders className="w-4 h-4" />
          <span>UI & Alert Preferences</span>
        </button>
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: FACILITY & ECONOMICS                                               */}
      {/* ========================================================================= */}
      {activeTab === 'facility' && (
        <form onSubmit={(e) => { e.preventDefault(); setIsConfirmOpen(true); }} className="space-y-6">
          {saveSuccess && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center gap-2 text-emerald-800 text-xs font-medium">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>Facility settings successfully saved to PostgreSQL database!</span>
            </div>
          )}

          {/* Section 1: Facility Branding */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
            <div className="flex items-center gap-2 mb-4 pb-3 border-b border-slate-100">
              <Building className="w-4 h-4 text-[#800000]" />
              <h2 className="text-sm font-semibold text-slate-900">Institution & Facility Profile</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Facility Name</label>
                <input
                  type="text"
                  value={facilityName}
                  onChange={(e) => setFacilityName(e.target.value)}
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#800000] focus:border-[#800000] outline-none text-slate-900"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Institution Name (e.g. Foundation University)</label>
                <input
                  type="text"
                  value={institution}
                  onChange={(e) => setInstitution(e.target.value)}
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#800000] focus:border-[#800000] outline-none text-slate-900"
                  required
                />
              </div>
            </div>
          </div>

          {/* Section 2: Economic Salvage Values */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
            <div className="flex items-center gap-2 mb-4 pb-3 border-b border-slate-100">
              <Coins className="w-4 h-4 text-amber-600" />
              <div>
                <h2 className="text-sm font-semibold text-slate-900">Economic Valuation & Utility Tariffs</h2>
                <p className="text-xs text-slate-500">Commercial market prices used for Day 10 salvage and energy cost reduction calculations.</p>
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Day-10 Penoy Unit Price (₱)</label>
                <div className="relative">
                  <span className="absolute left-3 top-2 text-xs text-slate-400 font-semibold">₱</span>
                  <input
                    type="number"
                    step="0.50"
                    min="0"
                    value={penoyPrice}
                    onChange={(e) => setPenoyPrice(Number(e.target.value))}
                    className="w-full text-xs pl-7 pr-3 py-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#800000] focus:border-[#800000] outline-none text-slate-900"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Day-28 Duckling Selling Price (₱)</label>
                <div className="relative">
                  <span className="absolute left-3 top-2 text-xs text-slate-400 font-semibold">₱</span>
                  <input
                    type="number"
                    step="1.00"
                    min="0"
                    value={ducklingPrice}
                    onChange={(e) => setDucklingPrice(Number(e.target.value))}
                    className="w-full text-xs pl-7 pr-3 py-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#800000] focus:border-[#800000] outline-none text-slate-900"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Electricity Tariff Rate (₱/kWh)</label>
                <div className="relative">
                  <span className="absolute left-3 top-2 text-xs text-slate-400 font-semibold">₱</span>
                  <input
                    type="number"
                    step="0.10"
                    min="0"
                    value={kwhRate}
                    onChange={(e) => setKwhRate(Number(e.target.value))}
                    className="w-full text-xs pl-7 pr-3 py-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#800000] focus:border-[#800000] outline-none text-slate-900"
                    required
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Section 3: AI & Hardware Conveyor Calibration */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
            <div className="flex items-center gap-2 mb-4 pb-3 border-b border-slate-100">
              <Zap className="w-4 h-4 text-emerald-600" />
              <h2 className="text-sm font-semibold text-slate-900">AI Vision & Conveyor Sorter Parameters</h2>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="text-xs font-medium text-slate-700">YOLOv8 Confidence Threshold</label>
                  <span className="text-xs font-bold text-slate-900">{(confidenceThreshold * 100).toFixed(0)}%</span>
                </div>
                <input
                  type="range"
                  min="0.50"
                  max="0.99"
                  step="0.01"
                  value={confidenceThreshold}
                  onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
                  className="w-full accent-[#800000] cursor-pointer"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Conveyor Speed (cm/s)</label>
                <input
                  type="number"
                  step="0.5"
                  min="1"
                  value={conveyorSpeed}
                  onChange={(e) => setConveyorSpeed(Number(e.target.value))}
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#800000] focus:border-[#800000] outline-none text-slate-900"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Sensor to Chute Distance (cm)</label>
                <input
                  type="number"
                  step="1.0"
                  min="5"
                  value={conveyorDistance}
                  onChange={(e) => setConveyorDistance(Number(e.target.value))}
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#800000] focus:border-[#800000] outline-none text-slate-900"
                />
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={fetchSettings}
              className="px-4 py-2 border border-slate-300 text-xs font-medium text-slate-700 rounded-lg hover:bg-slate-50 transition-colors"
            >
              Reset to Saved
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="flex items-center gap-1.5 px-4 py-2 bg-[#800000] hover:bg-[#5C0000] text-white text-xs font-semibold rounded-lg shadow-xs transition-colors disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              <span>{isSaving ? 'Saving Changes...' : 'Save Facility Constants'}</span>
            </button>
          </div>
        </form>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: MY PROFILE & PASSWORD                                              */}
      {/* ========================================================================= */}
      {activeTab === 'account' && (
        <div className="space-y-6">
          {/* Account Details Card */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100 mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-[#800000]/10 border border-[#800000]/20 flex items-center justify-center text-[#800000] font-bold text-base">
                  {user?.full_name?.charAt(0).toUpperCase() || 'U'}
                </div>
                <div>
                  <h2 className="text-sm font-semibold text-slate-900">{user?.full_name}</h2>
                  <p className="text-xs text-slate-500">{user?.email}</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span
                  className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold border ${
                    user?.role === 'ADMIN'
                      ? 'bg-red-50 text-[#800000] border-red-200'
                      : user?.role === 'MANAGER'
                      ? 'bg-blue-50 text-blue-800 border-blue-200'
                      : 'bg-slate-100 text-slate-700 border-slate-200'
                  }`}
                >
                  {user?.role || 'OPERATOR'}
                </span>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 shrink-0" />
                  Active
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                <span className="text-slate-500 block mb-0.5">Account ID</span>
                <span className="font-mono text-slate-800 break-all">{user?.user_id}</span>
              </div>
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                <span className="text-slate-500 block mb-0.5">Registration Date</span>
                <span className="text-slate-800">
                  {user?.created_at ? new Date(user.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) : 'Official Hatchery Account'}
                </span>
              </div>
            </div>
          </div>

          {/* Edit Profile Name Form */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
            <div className="flex items-center gap-2 mb-4 pb-3 border-b border-slate-100">
              <UserIcon className="w-4 h-4 text-[#800000]" />
              <h2 className="text-sm font-semibold text-slate-900">Edit Profile Information</h2>
            </div>

            {profileSuccess && (
              <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center gap-2 text-emerald-800 text-xs font-medium">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>Profile name updated successfully!</span>
              </div>
            )}

            {profileError && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-800 text-xs font-medium">
                <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
                <span>{profileError}</span>
              </div>
            )}

            <form onSubmit={handleUpdateProfile} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Display Name / Research Title</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Engr. Ryle Gabotero (Lead Researcher)"
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#800000] focus:border-[#800000] outline-none text-slate-900"
                  required
                />
                <p className="text-xs text-slate-400 mt-1">This name will appear on candling session records and official PDF certificates.</p>
              </div>

              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={isSavingProfile || fullName === user?.full_name}
                  className="flex items-center gap-1.5 px-4 py-2 bg-[#800000] hover:bg-[#5C0000] text-white text-xs font-semibold rounded-lg shadow-xs transition-colors disabled:opacity-50"
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>{isSavingProfile ? 'Saving...' : 'Update Name'}</span>
                </button>
              </div>
            </form>
          </div>

          {/* Change Password Form */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
            <div className="flex items-center gap-2 mb-4 pb-3 border-b border-slate-100">
              <Key className="w-4 h-4 text-amber-600" />
              <div>
                <h2 className="text-sm font-semibold text-slate-900">Change Account Password</h2>
                <p className="text-xs text-slate-500">Ensure your new password contains at least 6 characters.</p>
              </div>
            </div>

            {passwordSuccess && (
              <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center gap-2 text-emerald-800 text-xs font-medium">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>Password changed successfully! Keep your new credentials secure.</span>
              </div>
            )}

            {passwordError && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-800 text-xs font-medium">
                <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
                <span>{passwordError}</span>
              </div>
            )}

            <form onSubmit={handleChangePassword} className="space-y-4 max-w-lg">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Current Password</label>
                <div className="relative">
                  <input
                    type={showCurrentPassword ? 'text' : 'password'}
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    className="w-full text-xs px-3 py-2 pr-9 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#800000] focus:border-[#800000] outline-none text-slate-900"
                    placeholder="Enter current password"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                    className="absolute right-2.5 top-2 text-slate-400 hover:text-slate-600"
                  >
                    {showCurrentPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">New Password</label>
                <div className="relative">
                  <input
                    type={showNewPassword ? 'text' : 'password'}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="w-full text-xs px-3 py-2 pr-9 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#800000] focus:border-[#800000] outline-none text-slate-900"
                    placeholder="Minimum 6 characters"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    className="absolute right-2.5 top-2 text-slate-400 hover:text-slate-600"
                  >
                    {showNewPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Confirm New Password</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#800000] focus:border-[#800000] outline-none text-slate-900"
                  placeholder="Re-enter new password"
                  required
                />
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={isChangingPassword || !currentPassword || !newPassword}
                  className="flex items-center gap-1.5 px-4 py-2 bg-[#800000] hover:bg-[#5C0000] text-white text-xs font-semibold rounded-lg shadow-xs transition-colors disabled:opacity-50"
                >
                  <Key className="w-3.5 h-3.5" />
                  <span>{isChangingPassword ? 'Changing Password...' : 'Update Password'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 3: DATABASE BACKUPS                                                   */}
      {/* ========================================================================= */}
      {activeTab === 'backups' && (
        <div className="space-y-6">
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Database className="w-5 h-5 text-[#800000]" />
                <div>
                  <h2 className="text-sm font-semibold text-slate-900">Automated PostgreSQL Database Snapshots</h2>
                  <p className="text-xs text-slate-500">Generate gzip-compressed JSON archives of all batches, scans, users, and audit logs.</p>
                </div>
              </div>

              <button
                onClick={handleCreateBackup}
                disabled={isCreatingBackup}
                className="flex items-center gap-1.5 px-3.5 py-2 bg-[#800000] hover:bg-[#5C0000] text-white text-xs font-semibold rounded-lg shadow-xs transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isCreatingBackup ? 'animate-spin' : ''}`} />
                <span>{isCreatingBackup ? 'Generating Snapshot...' : 'Create Backup Snapshot'}</span>
              </button>
            </div>

            {backupSuccess && (
              <div className="mt-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center gap-2 text-emerald-800 text-xs font-medium">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>New database backup snapshot created successfully!</span>
              </div>
            )}

            <div className="mt-5">
              <h3 className="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-3">Available Backup Archives</h3>

              {isLoadingBackups ? (
                <div className="py-8 text-center text-xs text-slate-400">Loading backup catalog...</div>
              ) : backups.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-400 bg-slate-50 rounded-lg border border-dashed border-slate-200">
                  No backup archives found. Click "Create Backup Snapshot" to generate the first archive.
                </div>
              ) : (
                <div className="overflow-x-auto border border-slate-200 rounded-lg">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                      <tr>
                        <th className="px-4 py-2.5">Archive Filename</th>
                        <th className="px-4 py-2.5">Size</th>
                        <th className="px-4 py-2.5">Timestamp (UTC)</th>
                        <th className="px-4 py-2.5 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {backups.map((b) => (
                        <tr key={b.filename} className="hover:bg-slate-50/80">
                          <td className="px-4 py-3 font-mono text-slate-800 font-medium">{b.filename}</td>
                          <td className="px-4 py-3 text-slate-600">{b.file_size_kb} KB</td>
                          <td className="px-4 py-3 text-slate-500">{new Date(b.created_at).toLocaleString()}</td>
                          <td className="px-4 py-3 text-right">
                            <a
                              href={apiClient.downloadBackupUrl(b.filename)}
                              download={b.filename}
                              className="inline-flex items-center gap-1 text-xs font-semibold text-[#800000] hover:text-[#5C0000] bg-red-50 px-2.5 py-1 rounded border border-red-200"
                            >
                              <Download className="w-3 h-3" />
                              <span>Download .gz</span>
                            </a>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 4: UI & ALERT PREFERENCES                                             */}
      {/* ========================================================================= */}
      {activeTab === 'preferences' && (
        <form onSubmit={handleSavePreferences} className="space-y-6">
          {prefSaved && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center gap-2 text-emerald-800 text-xs font-medium">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>Display and notification preferences saved to browser storage!</span>
            </div>
          )}

          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-5">
            <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
              <Sliders className="w-4 h-4 text-[#800000]" />
              <div>
                <h2 className="text-sm font-semibold text-slate-900">Dashboard Operational Preferences</h2>
                <p className="text-xs text-slate-500">Configure background polling speed and sensory alert chimes.</p>
              </div>
            </div>

            {/* Polling Interval */}
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Background Data Polling Frequency
              </label>
              <select
                value={pollingInterval}
                onChange={(e) => setPollingInterval(Number(e.target.value))}
                className="w-full sm:w-72 text-xs px-3 py-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#800000] focus:border-[#800000] outline-none text-slate-900"
              >
                <option value={5}>5 seconds (Real-time Live Candling)</option>
                <option value={10}>10 seconds (Standard Operational)</option>
                <option value={30}>30 seconds (Low Network Usage)</option>
                <option value={0}>Manual Refresh Only</option>
              </select>
              <p className="text-xs text-slate-400 mt-1">Controls how often the dashboard polls PostgreSQL for active egg scans.</p>
            </div>

            {/* Audio Alerts */}
            <div className="flex items-start justify-between pt-3 border-t border-slate-100">
              <div>
                <span className="text-xs font-semibold text-slate-900 block">Biological Anomaly Audio Alerts</span>
                <span className="text-xs text-slate-500">Play an audible chime when a batch drops below baseline fertility (&gt;15% drop).</span>
              </div>
              <input
                type="checkbox"
                checked={audioAlerts}
                onChange={(e) => setAudioAlerts(e.target.checked)}
                className="mt-1 w-4 h-4 accent-[#800000] rounded cursor-pointer"
              />
            </div>

            {/* Table Density */}
            <div className="flex items-start justify-between pt-3 border-t border-slate-100">
              <div>
                <span className="text-xs font-semibold text-slate-900 block">Scan Explorer Table Density</span>
                <span className="text-xs text-slate-500">Choose between compact high-density view or spaced cards.</span>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setTableDensity('compact')}
                  className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors ${
                    tableDensity === 'compact'
                      ? 'bg-[#800000] text-white border-[#800000]'
                      : 'border-slate-300 text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  Compact
                </button>
                <button
                  type="button"
                  onClick={() => setTableDensity('comfortable')}
                  className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors ${
                    tableDensity === 'comfortable'
                      ? 'bg-[#800000] text-white border-[#800000]'
                      : 'border-slate-300 text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  Comfortable
                </button>
              </div>
            </div>
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              className="flex items-center gap-1.5 px-4 py-2 bg-[#800000] hover:bg-[#5C0000] text-white text-xs font-semibold rounded-lg shadow-xs transition-colors"
            >
              <Save className="w-3.5 h-3.5" />
              <span>Save UI Preferences</span>
            </button>
          </div>
        </form>
      )}

      {/* Confirmation Modal for Facility Parameters */}
      <ConfirmationModal
        isOpen={isConfirmOpen}
        onClose={() => setIsConfirmOpen(false)}
        onConfirm={handleExecuteSaveFacility}
        title="Confirm Facility Parameter Changes"
        description="You are about to modify system-wide economic constants and hardware parameters. This will update future financial yield projections."
        diffs={calculateDiffs()}
        confirmText="Save Changes"
        cancelText="Discard"
        variant="primary"
        isLoading={isSaving}
      />
    </div>
  );
};

export default SettingsPage;
