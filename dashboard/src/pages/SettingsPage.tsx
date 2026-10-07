import { readPreferences, savePreferences } from '../hooks/usePreferences';
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
import { Badge } from '../components/Badge';

type SettingsTab = 'facility' | 'account' | 'backups' | 'preferences';

interface BackupArchive {
  filename: string;
  file_size_kb: number;
  created_at: string;
}

export const SettingsPage: React.FC = () => {
  const { user, updateUser } = useAuth();
  const canManage = user?.role === 'ADMIN' || user?.role === 'MANAGER';
  const [saveError, setSaveError] = useState<string | null>(null);
  const [backupError, setBackupError] = useState<string | null>(null);
  const [backupListError, setBackupListError] = useState<string | null>(null);
  const [hasLoadedBackups, setHasLoadedBackups] = useState(false);
  const [downloadingBackup, setDownloadingBackup] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [failedDownload, setFailedDownload] = useState<string | null>(null);
  const [theme, setTheme] = useState<'light' | 'dark'>(() => readPreferences().theme);
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get('tab') as SettingsTab | null;

  const [activeTab, setActiveTab] = useState<SettingsTab>(() => {
    if (tabParam && (canManage || ['account', 'preferences'].includes(tabParam)) && ['facility', 'account', 'backups', 'preferences'].includes(tabParam)) {
      return tabParam;
    }
    return canManage ? 'facility' : 'account';
  });

  useEffect(() => {
    if (tabParam && (canManage || ['account', 'preferences'].includes(tabParam)) && ['facility', 'account', 'backups', 'preferences'].includes(tabParam)) {
      setActiveTab(tabParam);
    }
    if (!canManage && (activeTab === 'facility' || activeTab === 'backups')) {
      setActiveTab('account');
    }
  }, [tabParam, canManage, activeTab]);

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
    return readPreferences().pollingInterval;
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
      if (!data || typeof data !== 'object') throw new Error('Invalid settings response');
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
    setBackupListError(null);
    try {
      const data = await apiClient.getBackups();
      if (!Array.isArray(data)) throw new Error('Invalid backup catalog response');
      setBackups(data);
      setHasLoadedBackups(true);
    } catch {
      setBackupListError(hasLoadedBackups
        ? 'Backup records could not be refreshed. Previously loaded archives are shown and may be out of date.'
        : 'Backup records could not be loaded. Retry to check the available archives.');
    } finally {
      setIsLoadingBackups(false);
    }
  };

  const handleDownloadBackup = async (filename: string) => {
    if (downloadingBackup) return;
    setDownloadingBackup(filename);
    setDownloadError(null);
    setFailedDownload(null);
    try {
      const blob = await apiClient.downloadBackup(filename);
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = objectUrl;
      link.download = filename;
      document.body.appendChild(link);
      try {
        link.click();
      } finally {
        link.remove();
        // Keep the URL alive until the browser has started the download.
        window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
      }
    } catch {
      setDownloadError(`The archive ${filename} could not be downloaded. Retry the download.`);
      setFailedDownload(filename);
    } finally {
      setDownloadingBackup(null);
    }
  };

  useEffect(() => {
    if (canManage) fetchSettings();
    else setIsLoading(false);
  }, [canManage]);

  useEffect(() => {
    if (canManage && activeTab === 'backups') {
      fetchBackupsList();
    }
  }, [activeTab, canManage]);

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
    if (originalFacility.conveyor_distance_cm !== conveyorDistance) {
      diffs.push({ label: 'Sensor to chute distance', oldValue: `${originalFacility.conveyor_distance_cm} cm`, newValue: `${conveyorDistance} cm` });
    }
    return diffs;
  };

  const handleExecuteSaveFacility = async () => {
    setIsSaving(true);
    setSaveError(null);
    setSaveSuccess(false);
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
      setSaveError('Settings could not be saved. Your edits are retained. Try saving again.');
      setIsConfirmOpen(false);
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
    setBackupError(null);
    try {
      await apiClient.createBackup();
      setBackupSuccess(true);
      await fetchBackupsList();
      setTimeout(() => setBackupSuccess(false), 4000);
    } catch (err) {
      setBackupError('The backup could not be created. Try again.');
    } finally {
      setIsCreatingBackup(false);
    }
  };

  const handleSavePreferences = (e: React.FormEvent) => {
    e.preventDefault();
    savePreferences({ pollingInterval, tableDensity, theme });
    setPrefSaved(true);
    setTimeout(() => setPrefSaved(false), 3000);
  };

  return (
    <div className="space-y-6 max-w-4xl min-w-0 pb-8">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1>Settings &amp; System Preferences</h1>
          <p className="page-description">
            Manage institutional constants, your user credentials, database backup archives, and UI alerts.
          </p>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="page-actions border-b border-border pb-3" role="group" aria-label="Settings sections">
        {canManage && <button
          type="button"
          aria-pressed={activeTab === 'facility'}
          onClick={() => handleTabChange('facility')}
          className={activeTab === 'facility' ? 'primary-action' : 'secondary-action'}
        >
          <Building aria-hidden="true" className="w-4 h-4" />
          <span>Facility & Economics</span>
        </button>}

        <button
          type="button"
          aria-pressed={activeTab === 'account'}
          onClick={() => handleTabChange('account')}
          className={activeTab === 'account' ? 'primary-action' : 'secondary-action'}
        >
          <UserIcon aria-hidden="true" className="w-4 h-4" />
          <span>My Profile & Password</span>
        </button>

        {canManage && <button
          type="button"
          aria-pressed={activeTab === 'backups'}
          onClick={() => handleTabChange('backups')}
          className={activeTab === 'backups' ? 'primary-action' : 'secondary-action'}
        >
          <HardDrive aria-hidden="true" className="w-4 h-4" />
          <span>Database Backups</span>
        </button>}

        <button
          type="button"
          aria-pressed={activeTab === 'preferences'}
          onClick={() => handleTabChange('preferences')}
          className={activeTab === 'preferences' ? 'primary-action' : 'secondary-action'}
        >
          <Sliders aria-hidden="true" className="w-4 h-4" />
          <span>Display preferences</span>
        </button>
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: FACILITY & ECONOMICS                                               */}
      {/* ========================================================================= */}
      {canManage && activeTab === 'facility' && isError && !originalFacility && (
        <DataUnavailableState
          title="Settings Service Offline"
          description="Unable to load persistent facility settings. Account and display preferences remain available in the sections above."
          onRetry={fetchSettings}
          isRetrying={isLoading}
        />
      )}
      {canManage && activeTab === 'facility' && isLoading && !originalFacility && <div role="status" aria-busy="true" className="fu-card p-6 space-y-4"><p className="text-slate-600">Loading facility settings…</p><div aria-hidden="true" className="h-24 bg-slate-100 rounded animate-pulse" /></div>}
      {canManage && activeTab === 'facility' && isError && originalFacility && <div role="alert" className="feedback-warning space-y-3"><p>Facility settings could not be refreshed. Previously loaded values and your edits are retained and may be out of date.</p><button type="button" onClick={() => { void fetchSettings(); }} disabled={isLoading} className="secondary-action"><RefreshCw aria-hidden="true" />Retry</button></div>}
      {canManage && activeTab === 'facility' && isLoading && originalFacility && <p role="status" className="text-slate-600">Refreshing facility settings…</p>}
      {canManage && activeTab === 'facility' && originalFacility && (
        <form onSubmit={(e) => { e.preventDefault(); setIsConfirmOpen(true); }} className="space-y-6">
          {saveError && <p role="alert" className="p-4 bg-red-50 text-red-800 border border-red-300 rounded-xl">{saveError}</p>}
          {saveSuccess && (
            <div role="status" className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center gap-2 text-emerald-800 text-sm font-medium">
              <CheckCircle2 aria-hidden="true" className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>Facility settings successfully saved to PostgreSQL database!</span>
            </div>
          )}

          {/* Section 1: Facility Branding */}
          <div className="fu-card p-5">
            <div className="flex items-center gap-2 mb-4 pb-3 border-b border-slate-100">
              <Building aria-hidden="true" className="w-4 h-4 text-brand" />
              <h2 className="section-heading">Institution & Facility Profile</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="settingspage-field-1" className="block text-sm font-medium text-slate-700 mb-1">Facility Name</label>
                <input id="settingspage-field-1"
                  type="text"
                  value={facilityName}
                  onChange={(e) => setFacilityName(e.target.value)}
                  className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#800000] focus:border-[#800000] outline-none text-slate-900"
                  required
                />
              </div>
              <div>
                <label htmlFor="settingspage-field-2" className="block text-sm font-medium text-slate-700 mb-1">Institution Name (e.g. Foundation University)</label>
                <input id="settingspage-field-2"
                  type="text"
                  value={institution}
                  onChange={(e) => setInstitution(e.target.value)}
                  className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#800000] focus:border-[#800000] outline-none text-slate-900"
                  required
                />
              </div>
            </div>
          </div>

          {/* Section 2: Economic Salvage Values */}
          <div className="fu-card p-5">
            <div className="flex items-center gap-2 mb-4 pb-3 border-b border-slate-100">
              <Coins aria-hidden="true" className="w-4 h-4 text-amber-600" />
              <div>
                <h2 className="section-heading">Economic Valuation & Utility Tariffs</h2>
                <p className="text-sm text-slate-500">Commercial market prices used for Day 10 salvage and energy cost reduction calculations.</p>
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label htmlFor="settingspage-day-10-penoy-unit-price" className="block text-sm font-medium text-slate-700 mb-1">Day-10 Penoy Unit Price (₱)</label>
                <div className="relative">
                  <span aria-hidden="true" className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-slate-600 font-semibold">₱</span>
                  <input id="settingspage-day-10-penoy-unit-price"
                    type="number"
                    step="0.50"
                    min="0"
                    value={penoyPrice}
                    onChange={(e) => setPenoyPrice(Number(e.target.value))}
                    className="w-full text-sm pl-7 pr-3 py-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#800000] focus:border-[#800000] outline-none text-slate-900"
                    required
                  />
                </div>
              </div>

              <div>
                <label htmlFor="settingspage-day-28-duckling-selling-price" className="block text-sm font-medium text-slate-700 mb-1">Day-28 Duckling Selling Price (₱)</label>
                <div className="relative">
                  <span aria-hidden="true" className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-slate-600 font-semibold">₱</span>
                  <input id="settingspage-day-28-duckling-selling-price"
                    type="number"
                    step="1.00"
                    min="0"
                    value={ducklingPrice}
                    onChange={(e) => setDucklingPrice(Number(e.target.value))}
                    className="w-full text-sm pl-7 pr-3 py-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#800000] focus:border-[#800000] outline-none text-slate-900"
                    required
                  />
                </div>
              </div>

              <div>
                <label htmlFor="settingspage-electricity-tariff-rate-kwh" className="block text-sm font-medium text-slate-700 mb-1">Electricity Tariff Rate (₱/kWh)</label>
                <div className="relative">
                  <span aria-hidden="true" className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-slate-600 font-semibold">₱</span>
                  <input id="settingspage-electricity-tariff-rate-kwh"
                    type="number"
                    step="0.10"
                    min="0"
                    value={kwhRate}
                    onChange={(e) => setKwhRate(Number(e.target.value))}
                    className="w-full text-sm pl-7 pr-3 py-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#800000] focus:border-[#800000] outline-none text-slate-900"
                    required
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Section 3: AI & Hardware Conveyor Calibration */}
          <div className="fu-card p-5">
            <div className="flex items-center gap-2 mb-4 pb-3 border-b border-slate-100">
              <Zap aria-hidden="true" className="w-4 h-4 text-emerald-600" />
              <h2 className="section-heading">AI Vision & Conveyor Sorter Parameters</h2>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <div className="flex flex-wrap justify-between items-center gap-2 mb-1">
                  <label htmlFor="settingspage-yolov8-confidence-threshold" className="text-sm font-medium text-slate-700">YOLOv8 Confidence Threshold</label>
                  <span className="text-sm font-bold text-slate-900">{(confidenceThreshold * 100).toFixed(0)}%</span>
                </div>
                <input id="settingspage-yolov8-confidence-threshold"
                  type="range"
                  min="0.75"
                  max="0.99"
                  step="0.01"
                  value={confidenceThreshold}
                  onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
                  className="w-full accent-[#800000] cursor-pointer"
                />
              </div>

              <div>
                <label htmlFor="settingspage-field-3" className="block text-sm font-medium text-slate-700 mb-1">Conveyor Speed (cm/s)</label>
                <input id="settingspage-field-3"
                  type="number"
                  step="0.5"
                  min="1"
                  value={conveyorSpeed}
                  onChange={(e) => setConveyorSpeed(Number(e.target.value))}
                  className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#800000] focus:border-[#800000] outline-none text-slate-900"
                />
              </div>

              <div>
                <label htmlFor="settingspage-field-4" className="block text-sm font-medium text-slate-700 mb-1">Sensor to Chute Distance (cm)</label>
                <input id="settingspage-field-4"
                  type="number"
                  step="1.0"
                  min="5"
                  value={conveyorDistance}
                  onChange={(e) => setConveyorDistance(Number(e.target.value))}
                  className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#800000] focus:border-[#800000] outline-none text-slate-900"
                />
              </div>
            </div>
          </div>

          <div className="page-actions justify-end pt-2">
            <button
              type="button"
              onClick={fetchSettings}
              disabled={isLoading || isSaving}
              className="secondary-action"
            >
              <RefreshCw aria-hidden="true" />
              Reset to Saved
            </button>
            <button
              type="submit"
              disabled={isSaving || isLoading}
              className="primary-action"
            >
              <Save aria-hidden="true" className="w-4 h-4" />
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
          <div className="fu-card p-5">
            <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-border mb-4">
              <div className="flex items-center gap-3 min-w-0">
                <div aria-hidden="true" className="shrink-0 w-10 h-10 rounded-full bg-[#800000]/10 border border-[#800000]/20 flex items-center justify-center text-brand font-bold text-base">
                  {user?.full_name?.charAt(0).toUpperCase() || 'U'}
                </div>
                <div className="min-w-0">
                  <h2 className="font-semibold text-foreground [overflow-wrap:anywhere]">{user?.full_name}</h2>
                  <p className="text-slate-600 [overflow-wrap:anywhere]">{user?.email}</p>
                </div>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                <Badge type="role" value={user?.role || 'OPERATOR'} />
                <Badge value={user?.is_active ? 'ACTIVE' : 'INACTIVE'} />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
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
          <div className="fu-card p-5">
            <div className="flex items-center gap-2 mb-4 pb-3 border-b border-slate-100">
              <UserIcon aria-hidden="true" className="w-4 h-4 text-brand" />
              <h2 className="section-heading">Edit Profile Information</h2>
            </div>

            {profileSuccess && (
              <div role="status" className="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center gap-2 text-emerald-800 text-sm font-medium">
                <CheckCircle2 aria-hidden="true" className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>Profile name updated successfully!</span>
              </div>
            )}

            {profileError && (
              <div role="alert" className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-800 text-sm font-medium">
                <AlertTriangle aria-hidden="true" className="w-4 h-4 text-red-600 shrink-0" />
                <span>{profileError}</span>
              </div>
            )}

            <form onSubmit={handleUpdateProfile} className="space-y-4">
              <div>
                <label htmlFor="settingspage-field-5" className="block text-sm font-medium text-slate-700 mb-1">Display Name / Research Title</label>
                <input id="settingspage-field-5"
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Engr. Ryle Gabotero (Lead Researcher)"
                  className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#800000] focus:border-[#800000] outline-none text-slate-900"
                  required
                />
                <p className="text-sm text-slate-600 mt-1">This name will appear on candling session records and official PDF certificates.</p>
              </div>

              <div className="page-actions justify-end">
                <button
                  type="submit"
                  disabled={isSavingProfile || fullName === user?.full_name}
                  className="primary-action"
                >
                  <Save aria-hidden="true" className="w-3.5 h-3.5" />
                  <span>{isSavingProfile ? 'Saving...' : 'Update Name'}</span>
                </button>
              </div>
            </form>
          </div>

          {/* Change Password Form */}
          <div className="fu-card p-5">
            <div className="flex items-center gap-2 mb-4 pb-3 border-b border-slate-100">
              <Key aria-hidden="true" className="w-4 h-4 text-amber-600" />
              <div>
                <h2 className="section-heading">Change Account Password</h2>
                <p className="text-sm text-slate-500">Ensure your new password contains at least 6 characters.</p>
              </div>
            </div>

            {passwordSuccess && (
              <div role="status" className="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center gap-2 text-emerald-800 text-sm font-medium">
                <CheckCircle2 aria-hidden="true" className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>Password changed successfully! Keep your new credentials secure.</span>
              </div>
            )}

            {passwordError && (
              <div role="alert" className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-800 text-sm font-medium">
                <AlertTriangle aria-hidden="true" className="w-4 h-4 text-red-600 shrink-0" />
                <span>{passwordError}</span>
              </div>
            )}

            <form onSubmit={handleChangePassword} className="space-y-4 max-w-lg">
              <div>
                <label htmlFor="settingspage-field-6" className="block text-sm font-medium text-slate-700 mb-1">Current Password</label>
                <div className="relative">
                  <input id="settingspage-field-6"
                    type={showCurrentPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    className="w-full text-sm px-3 py-2 pr-12 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#800000] focus:border-[#800000] outline-none text-slate-900"
                    placeholder="Enter current password"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                    aria-label={showCurrentPassword ? 'Hide current password' : 'Show current password'}
                    aria-pressed={showCurrentPassword}
                    className="absolute right-0 top-1/2 -translate-y-1/2 min-h-11 w-11 flex items-center justify-center rounded-lg text-slate-600 hover:bg-slate-100 hover:text-foreground"
                  >
                    {showCurrentPassword ? <EyeOff aria-hidden="true" className="w-4 h-4" /> : <Eye aria-hidden="true" className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div>
                <label htmlFor="settingspage-field-7" className="block text-sm font-medium text-slate-700 mb-1">New Password</label>
                <div className="relative">
                  <input id="settingspage-field-7"
                    type={showNewPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="w-full text-sm px-3 py-2 pr-12 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#800000] focus:border-[#800000] outline-none text-slate-900"
                    placeholder="Minimum 6 characters"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    aria-label={showNewPassword ? 'Hide new password' : 'Show new password'}
                    aria-pressed={showNewPassword}
                    className="absolute right-0 top-1/2 -translate-y-1/2 min-h-11 w-11 flex items-center justify-center rounded-lg text-slate-600 hover:bg-slate-100 hover:text-foreground"
                  >
                    {showNewPassword ? <EyeOff aria-hidden="true" className="w-4 h-4" /> : <Eye aria-hidden="true" className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div>
                <label htmlFor="settingspage-field-8" className="block text-sm font-medium text-slate-700 mb-1">Confirm New Password</label>
                <input id="settingspage-field-8"
                  type="password"
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#800000] focus:border-[#800000] outline-none text-slate-900"
                  placeholder="Re-enter new password"
                  required
                />
              </div>

              <div className="page-actions pt-2">
                <button
                  type="submit"
                  disabled={isChangingPassword || !currentPassword || !newPassword}
                  className="primary-action"
                >
                  <Key aria-hidden="true" className="w-3.5 h-3.5" />
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
      {canManage && activeTab === 'backups' && (
        <div className="space-y-6">
          <div className="fu-card p-5">
            <div className="section-header pb-4 border-b border-border">
              <div className="flex items-start gap-2 min-w-0">
                <Database aria-hidden="true" className="w-5 h-5 text-brand shrink-0 mt-0.5" />
                <div>
                  <h2 className="section-heading">Automated PostgreSQL Database Snapshots</h2>
                  <p className="text-sm text-slate-500">Generate gzip-compressed JSON archives of all batches, scans, users, and audit logs.</p>
                </div>
              </div>

              <div className="page-actions">
                <button type="button" onClick={() => { void fetchBackupsList(); }} disabled={isLoadingBackups} className="secondary-action"><RefreshCw aria-hidden="true" />{isLoadingBackups ? 'Refreshing…' : 'Refresh archives'}</button>
                <button type="button" onClick={handleCreateBackup} disabled={isCreatingBackup} className="primary-action">
                  <Database aria-hidden="true" />
                  <span>{isCreatingBackup ? 'Generating Snapshot…' : 'Create Backup Snapshot'}</span>
                </button>
              </div>
            </div>

            {backupError && <div role="alert" className="mt-4 p-4 bg-red-50 text-red-800 border border-red-300 rounded-xl space-y-3"><p>{backupError}</p><button type="button" onClick={handleCreateBackup} disabled={isCreatingBackup} className="secondary-action"><RefreshCw aria-hidden="true" />Retry creating backup</button></div>}
            {downloadError && <div role="alert" className="mt-4 p-4 bg-red-50 text-red-800 border border-red-300 rounded-xl space-y-3 [overflow-wrap:anywhere]"><p>{downloadError}</p>{failedDownload && <button type="button" onClick={() => { void handleDownloadBackup(failedDownload); }} disabled={Boolean(downloadingBackup)} className="secondary-action"><Download aria-hidden="true" />Retry download</button>}</div>}
            {downloadingBackup && <p role="status" className="mt-4 text-slate-600 [overflow-wrap:anywhere]">Downloading {downloadingBackup}…</p>}
            {backupSuccess && (
              <div role="status" className="mt-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center gap-2 text-emerald-800 text-sm font-medium">
                <CheckCircle2 aria-hidden="true" className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>New database backup snapshot created successfully!</span>
              </div>
            )}

            <div className="mt-5">
              <h3 className="font-semibold text-foreground mb-3">Available Backup Archives</h3>

              {backupListError && <div role="alert" className="feedback-warning mb-4 space-y-3"><p>{backupListError}</p><button type="button" onClick={() => { void fetchBackupsList(); }} disabled={isLoadingBackups} className="secondary-action"><RefreshCw aria-hidden="true" />Retry loading archives</button></div>}
              {isLoadingBackups && <div role="status" aria-busy="true" className="py-4 text-slate-600">{hasLoadedBackups ? 'Refreshing backup catalog… Previously loaded archives remain visible.' : 'Loading backup catalog…'}</div>}
              {hasLoadedBackups && backups.length === 0 ? (
                <div className="py-8 text-center text-slate-600 bg-slate-50 rounded-lg border border-slate-200">
                  No backup archives found. Click "Create Backup Snapshot" to generate the first archive.
                </div>
              ) : hasLoadedBackups && backups.length > 0 ? (
                <div className="table-scroll bordered-table" tabIndex={0} role="region" aria-label="Backup archives table, scroll horizontally on smaller screens" aria-busy={isLoadingBackups}>
                  <table className="w-full min-w-[680px] text-left">
                    <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                      <tr>
                        <th scope="col" className="px-4 py-2.5">Archive Filename</th>
                        <th scope="col" className="px-4 py-2.5">Size</th>
                        <th scope="col" className="px-4 py-2.5">Created (local time)</th>
                        <th scope="col" className="px-4 py-2.5 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {backups.map((b) => (
                        <tr key={b.filename} className="hover:bg-slate-50/80">
                          <td className="px-4 py-3 font-mono text-slate-800 font-medium max-w-80 [overflow-wrap:anywhere]">{b.filename}</td>
                          <td className="px-4 py-3 text-slate-600">{b.file_size_kb} KB</td>
                          <td className="px-4 py-3 text-slate-500">{new Date(b.created_at).toLocaleString()}</td>
                          <td className="px-4 py-3 text-right">
                            <button
                              type="button"
                              onClick={() => { void handleDownloadBackup(b.filename); }}
                              disabled={Boolean(downloadingBackup)}
                              aria-label={`Download archive ${b.filename}`}
                              className="secondary-action"
                            >
                              <Download aria-hidden="true" />
                              <span>{downloadingBackup === b.filename ? 'Downloading…' : 'Download .gz'}</span>
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}
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
            <div role="status" className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center gap-2 text-emerald-800 text-sm font-medium">
              <CheckCircle2 aria-hidden="true" className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>Display and notification preferences saved to browser storage!</span>
            </div>
          )}

          <div className="fu-card p-5 space-y-5">
            <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
              <Sliders aria-hidden="true" className="w-4 h-4 text-brand" />
              <div>
                <h2 className="section-heading">Display preferences</h2>
                <p className="text-sm text-slate-500">Choose the scan refresh interval, appearance, and table spacing.</p>
              </div>
            </div>

            {/* Polling Interval */}
            <div>
              <label htmlFor="settingspage-field-9" className="block text-sm font-medium text-slate-700 mb-1">
                Background Data Polling Frequency
              </label>
              <select id="settingspage-field-9"
                value={pollingInterval}
                onChange={(e) => setPollingInterval(Number(e.target.value))}
                className="w-full sm:w-72 text-sm px-3 py-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-[#800000] focus:border-[#800000] outline-none text-slate-900"
              >
                <option value={5}>5 seconds (Real-time Live Candling)</option>
                <option value={10}>10 seconds (Standard Operational)</option>
                <option value={30}>30 seconds (Low Network Usage)</option>
                <option value={0}>Manual Refresh Only</option>
              </select>
              <p className="text-sm text-slate-600 mt-1">Controls how often the dashboard polls PostgreSQL for active egg scans.</p>
            </div>

            <div className="border-t border-slate-200 pt-4">
              <label htmlFor="dashboard-theme" className="block font-medium mb-2">Appearance</label>
              <select id="dashboard-theme" value={theme} onChange={e => setTheme(e.target.value as 'light' | 'dark')} className="border border-slate-300 rounded-lg px-3 py-2 bg-card">
                <option value="light">Light</option><option value="dark">Dark</option>
              </select>
            </div>

            {/* Table Density */}
            <div className="flex flex-col sm:flex-row gap-3 sm:items-start justify-between pt-3 border-t border-slate-100">
              <div>
                <span className="text-sm font-semibold text-slate-900 block">Scan Explorer Table Density</span>
                <span className="text-sm text-slate-500">Choose tighter or more spacious table rows.</span>
              </div>
              <div className="page-actions" role="group" aria-label="Table density">
                <button
                  type="button"
                  onClick={() => setTableDensity('compact')}
                  aria-pressed={tableDensity === 'compact'}
                  className={tableDensity === 'compact' ? 'primary-action' : 'secondary-action'}
                >
                  Compact
                </button>
                <button
                  type="button"
                  onClick={() => setTableDensity('comfortable')}
                  aria-pressed={tableDensity === 'comfortable'}
                  className={tableDensity === 'comfortable' ? 'primary-action' : 'secondary-action'}
                >
                  Comfortable
                </button>
              </div>
            </div>
          </div>

          <div className="page-actions justify-end">
            <button
              type="submit"
              className="primary-action"
            >
              <Save aria-hidden="true" className="w-3.5 h-3.5" />
              <span>Save UI Preferences</span>
            </button>
          </div>
        </form>
      )}

      {/* Confirmation Modal for Facility Parameters */}
      <ConfirmationModal
        isOpen={isConfirmOpen}
        onClose={() => { if (!isSaving) setIsConfirmOpen(false); }}
        onConfirm={handleExecuteSaveFacility}
        title="Confirm Facility Parameter Changes"
        description="You are about to modify system-wide economic constants and hardware parameters. This will update future financial yield projections."
        diffs={calculateDiffs()}
        confirmText="Save Changes"
        cancelText="Keep editing"
        variant="primary"
        isLoading={isSaving}
      />
    </div>
  );
};

export default SettingsPage;
