import { useAuth } from '../context/AuthContext';
import { deviceAvailability } from '../lib/deviceStatus';
import React, { useState, useEffect, useCallback } from 'react';
import {
  Cpu,
  RefreshCw,
  Sliders,
  CheckCircle2,
  Save,
  Camera,
  Layers,
  Radio,
  Wifi,
  WifiOff,
  Activity,
  HardDrive,
  Brain,
  ShieldCheck,
  Zap,
  Image as ImageIcon,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { Device } from '../types';
import { Badge } from '../components/Badge';
import { DataUnavailableState } from '../components/ui/DataUnavailableState';
import { EmptyState } from '../components/ui/EmptyState';

export const DevicesPage: React.FC = () => {
  const { user } = useAuth();
  const canCalibrate = user?.role === 'ADMIN' || user?.role === 'MANAGER';
  const [saveError, setSaveError] = useState<string | null>(null);
  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isError, setIsError] = useState(false);
  const [savingDeviceId, setSavingDeviceId] = useState<string | null>(null);
  const [probingDeviceId, setProbingDeviceId] = useState<string | null>(null);
  const [probeStatus, setProbeStatus] = useState<Record<string, { is_live: boolean; message: string }>>({});
  const [now, setNow] = useState(Date.now);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [snapshotUrl, setSnapshotUrl] = useState<Record<string, string | null>>({});
  const [loadingSnapshot, setLoadingSnapshot] = useState<Record<string, boolean>>({});

  // Calibration state per device
  const [calibration, setCalibration] = useState<Record<string, { speed: number; dist: number; pulse: number }>>({});

  const fetchDevices = useCallback(async (background = false) => {
    if (!background) setIsRefreshing(true);
    setIsError(false);
    try {
      const data = await apiClient.getDevices();
      const list = data || [];
      setDevices(list);
      setNow(Date.now());

      setSelectedDeviceId(prev => {
        if (prev && list.some(d => d.device_id === prev)) return prev;
        return list[0]?.device_id || null;
      });

      const calMap: Record<string, { speed: number; dist: number; pulse: number }> = {};
      list.forEach(d => {
        calMap[d.device_id] = {
          speed: d.conveyor_speed_cm_s || 12.5,
          dist: d.conveyor_dist_cm || 25.0,
          pulse: d.servo_pulse_ms || 250,
        };
      });
      setCalibration(previous => background ? { ...calMap, ...previous } : calMap);
    } catch (err) {
      console.error('Error fetching devices:', err);
      setIsError(true);
    } finally {
      if (!background) setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void fetchDevices();
    const poll = setInterval(() => { void fetchDevices(true); }, 15_000);
    const timer = setInterval(() => setNow(Date.now()), 30_000);
    return () => { clearInterval(timer); clearInterval(poll); };
  }, [fetchDevices]);

  const handleProbeDevice = async (deviceId: string) => {
    setProbingDeviceId(deviceId);
    try {
      const result = await apiClient.getDeviceLive(deviceId);
      setProbeStatus(prev => ({
        ...prev,
        [deviceId]: {
          is_live: result.is_live,
          message: result.is_live
            ? `Live connection confirmed at ${result.edge_url}`
            : `Edge app unreachable at ${result.edge_url}. Showing recorded data.`,
        },
      }));
      if (result.is_live && result.device) {
        setDevices(prev => prev.map(d => (d.device_id === deviceId ? { ...d, ...result.device, telemetry: result.telemetry } : d)));
      }
      setTimeout(() => {
        setProbeStatus(prev => {
          const next = { ...prev };
          delete next[deviceId];
          return next;
        });
      }, 5000);
    } catch {
      setProbeStatus(prev => ({
        ...prev,
        [deviceId]: { is_live: false, message: 'Probe failed. Edge app offline or unreachable.' },
      }));
    } finally {
      setProbingDeviceId(null);
    }
  };

  const handleFetchSnapshot = async (deviceId: string) => {
    setLoadingSnapshot(prev => ({ ...prev, [deviceId]: true }));
    try {
      const url = await apiClient.getDeviceCameraSnapshot(deviceId);
      setSnapshotUrl(prev => ({ ...prev, [deviceId]: url }));
    } catch {
      setSnapshotUrl(prev => ({ ...prev, [deviceId]: null }));
    } finally {
      setLoadingSnapshot(prev => ({ ...prev, [deviceId]: false }));
    }
  };

  const handleSaveCalibration = async (deviceId: string) => {
    const cal = calibration[deviceId];
    if (!cal) return;

    setSavingDeviceId(deviceId);
    setSaveError(null);
    setSaveMessage(null);
    try {
      await apiClient.updateDeviceCalibration(deviceId, {
        conveyor_speed_cm_s: cal.speed,
        conveyor_dist_cm: cal.dist,
        servo_pulse_ms: cal.pulse,
      });
      setSaveMessage(`Calibration record saved for ${deviceId}. Apply and verify these values in the edge application.`);
      setTimeout(() => setSaveMessage(null), 3000);
    } catch {
      setSaveError('Calibration could not be saved. Your edits are retained; try again.');
    } finally {
      setSavingDeviceId(null);
    }
  };

  const formatUptime = (seconds?: number) => {
    if (!seconds || seconds <= 0) return 'Just started';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    if (h > 0) return `${h}h ${m}m active`;
    return `${m}m active`;
  };

  // Fleet Aggregates
  const totalFleet = devices.length;
  const onlineFleet = devices.filter(d => ['ONLINE', 'SCANNING'].includes(deviceAvailability(d, now))).length;
  const totalUnsynced = devices.reduce((sum, d) => sum + (d.telemetry?.storage?.unsynced_scans || 0), 0);
  const healthRate = totalFleet > 0 ? Math.round((onlineFleet / totalFleet) * 100) : 100;

  const currentDevice = devices.find(d => d.device_id === selectedDeviceId) || devices[0];

  return (
    <div className="min-w-0 space-y-6 pb-8" aria-busy={isRefreshing}>
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1>Sorter devices</h1>
          <p className="page-description">
            Telemetry cockpit for physical Candling &amp; Sorting edge machines at Foundation University.
          </p>
        </div>

        <div className="page-actions">
          <button
            onClick={() => { void fetchDevices(); }}
            disabled={isRefreshing}
            className="secondary-action"
          >
            <RefreshCw aria-hidden="true" className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>{isRefreshing ? 'Refreshing…' : 'Refresh Edge Fleet'}</span>
          </button>
        </div>
      </div>

      {saveMessage && (
        <div role="status" className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-sm text-emerald-800 flex items-center gap-2">
          <CheckCircle2 aria-hidden="true" className="w-4 h-4 text-emerald-700 flex-shrink-0" />
          <span>{saveMessage}</span>
        </div>
      )}

      {saveError && <div role="alert" className="p-4 border border-red-300 rounded-xl bg-red-50 text-red-800">{saveError}</div>}
      {isError && devices.length > 0 && <p role="alert" className="text-amber-800">Refresh failed. Previously loaded device records are shown.</p>}

      {/* Fleet Summary Strip */}
      {devices.length > 0 && (
        <dl className="summary-strip grid grid-cols-2 lg:grid-cols-4 border border-border rounded-xl bg-card">
          <div className="px-4 py-4 sm:px-6">
            <dt className="text-xs font-medium text-slate-500 uppercase tracking-wide">Registered Sorters</dt>
            <dd className="text-2xl font-bold tabular-nums mt-1 text-foreground">{totalFleet}</dd>
            <dd className="text-xs text-slate-500 mt-1">Configured stations</dd>
          </div>
          <div className="px-4 py-4 sm:px-6 border-l border-border">
            <dt className="text-xs font-medium text-slate-500 uppercase tracking-wide">Online Stations</dt>
            <dd className="text-2xl font-bold tabular-nums mt-1 text-agri-green">{onlineFleet} / {totalFleet}</dd>
            <dd className="text-xs text-slate-500 mt-1">Transmitting heartbeats</dd>
          </div>
          <div className="px-4 py-4 sm:px-6 border-l border-border">
            <dt className="text-xs font-medium text-slate-500 uppercase tracking-wide">Fleet Availability</dt>
            <dd className="text-2xl font-bold tabular-nums mt-1 text-foreground">{healthRate}%</dd>
            <dd className="text-xs text-slate-500 mt-1">Operational coverage</dd>
          </div>
          <div className="px-4 py-4 sm:px-6 border-l border-border">
            <dt className="text-xs font-medium text-slate-500 uppercase tracking-wide">SQLite WAL Outbox</dt>
            <dd className="text-2xl font-bold tabular-nums mt-1 text-foreground">{totalUnsynced}</dd>
            <dd className="text-xs text-slate-500 mt-1">Pending scan records</dd>
          </div>
        </dl>
      )}

      {/* Empty / Error States */}
      {isError && devices.length === 0 ? (
        <DataUnavailableState
          title="Edge Stations Offline"
          description="Unable to connect to edge sorting hardware records in PostgreSQL. Ensure the backend REST service is reachable."
          onRetry={fetchDevices}
          isRetrying={isRefreshing}
        />
      ) : isRefreshing && devices.length === 0 ? (
        <div role="status" className="py-12 text-center text-slate-600">Loading device records…</div>
      ) : !isRefreshing && devices.length === 0 ? (
        <EmptyState
          title="No Sorter Stations Registered"
          description="No edge sorting machines (ESP32 / Raspberry Pi / Workstation) have registered with the central backend yet."
        />
      ) : (
        <div className="space-y-6">
          {/* Station Roster Bar */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1 custom-scrollbar border-b border-border" role="tablist" aria-label="Select Sorter Station">
            {devices.map(device => {
              const isSelected = device.device_id === (currentDevice?.device_id);
              const isOnline = ['ONLINE', 'SCANNING'].includes(deviceAvailability(device, now));
              return (
                <button
                  key={device.device_id}
                  role="tab"
                  aria-selected={isSelected}
                  onClick={() => setSelectedDeviceId(device.device_id)}
                  className={`flex items-center gap-2.5 px-4 py-2.5 font-medium text-xs whitespace-nowrap border-b-2 -mb-px transition-all ${
                    isSelected
                      ? 'border-brand text-brand font-semibold'
                      : 'border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300'
                  }`}
                >
                  <span className={`w-2 h-2 rounded-full shrink-0 ${isOnline ? 'bg-emerald-500 ring-2 ring-emerald-200' : 'bg-slate-400'}`} />
                  <span>{device.device_name}</span>
                  <span className="font-mono text-[11px] text-slate-400">({device.device_id})</span>
                </button>
              );
            })}
          </div>

          {/* 3-Column Split Cockpit Inspector */}
          {devices.map(device => {
            const isVisible = device.device_id === (currentDevice?.device_id);
            if (!isVisible) return null;

            const cal = calibration[device.device_id] || {
              speed: device.conveyor_speed_cm_s || 12.5,
              dist: device.conveyor_dist_cm || 25.0,
              pulse: device.servo_pulse_ms || 250,
            };

            const calculatedDelayMs = Math.round((cal.dist / cal.speed) * 1000);
            const t = device.telemetry;
            const isOnline = ['ONLINE', 'SCANNING'].includes(deviceAvailability(device, now));
            const probeInfo = probeStatus[device.device_id];
            const currentSnapshot = snapshotUrl[device.device_id];
            const isSnapshotLoading = loadingSnapshot[device.device_id];

            return (
              <div key={device.device_id} className="space-y-5 animate-in fade-in-50 duration-200">
                {/* Cockpit Station Header Card */}
                <div className="bg-card border border-border rounded-xl p-4 sm:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm">
                  <div className="flex items-center gap-3.5 min-w-0">
                    <div className="relative">
                      <div className="w-12 h-12 rounded-xl bg-maroon-50 text-brand border border-maroon-200 flex items-center justify-center font-bold shrink-0">
                        <Cpu aria-hidden="true" className="w-6 h-6" />
                      </div>
                      {isOnline && (
                        <span className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-emerald-500 ring-2 ring-card animate-pulse" />
                      )}
                    </div>

                    <div className="min-w-0">
                      <div className="flex items-center gap-2.5 flex-wrap">
                        <h2 className="text-base sm:text-lg font-bold text-foreground break-words">{device.device_name}</h2>
                        <Badge type="device" value={deviceAvailability(device, now)} />
                      </div>
                      <div className="flex items-center gap-2 text-xs text-slate-500 mt-1 flex-wrap font-mono">
                        <span>ID: {device.device_id}</span>
                        <span>•</span>
                        <span>IP: {device.ip_address || 'Not reported'}</span>
                        <span>•</span>
                        <span>Last ping: {device.last_heartbeat ? new Date(device.last_heartbeat).toLocaleTimeString('en-PH', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : 'Never'}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2.5 self-start md:self-auto shrink-0">
                    <button
                      onClick={() => handleProbeDevice(device.device_id)}
                      disabled={probingDeviceId === device.device_id}
                      className="secondary-action text-xs"
                      title="Directly ping the edge app's embedded HTTP diagnostic API"
                    >
                      <Radio aria-hidden="true" className={`w-3.5 h-3.5 text-brand ${probingDeviceId === device.device_id ? 'animate-spin' : ''}`} />
                      <span>{probingDeviceId === device.device_id ? 'Probing…' : 'Probe Live Edge'}</span>
                    </button>
                  </div>
                </div>

                {probeInfo && (
                  <div role="status" className={`p-3 rounded-xl text-xs flex items-center gap-2.5 border ${
                    probeInfo.is_live
                      ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                      : 'bg-amber-50 text-amber-800 border-amber-200'
                  }`}>
                    {probeInfo.is_live ? <Wifi className="w-4 h-4 shrink-0 text-emerald-600" aria-hidden="true" /> : <WifiOff className="w-4 h-4 shrink-0 text-amber-600" aria-hidden="true" />}
                    <span className="font-medium">{probeInfo.message}</span>
                  </div>
                )}

                {/* 3-Column Operational Cockpit Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
                  {/* Column 1: Host & Connectivity */}
                  <div className="bg-card border border-border rounded-xl p-5 space-y-4 shadow-sm flex flex-col justify-between">
                    <div className="space-y-3.5">
                      <div className="flex items-center gap-2 pb-2.5 border-b border-border">
                        <Activity className="w-4 h-4 text-brand" aria-hidden="true" />
                        <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">1. Host &amp; Connectivity</h3>
                      </div>

                      <dl className="space-y-2.5 text-xs">
                        <div className="flex justify-between py-1 border-b border-slate-100">
                          <dt className="text-slate-500">System Hostname</dt>
                          <dd className="font-mono font-medium text-foreground">{t?.hostname || device.device_id}</dd>
                        </div>
                        <div className="flex justify-between py-1 border-b border-slate-100">
                          <dt className="text-slate-500">Local LAN IP</dt>
                          <dd className="font-mono font-semibold text-brand">{device.ip_address || '127.0.0.1'}</dd>
                        </div>
                        <div className="flex justify-between py-1 border-b border-slate-100">
                          <dt className="text-slate-500">Edge API Port</dt>
                          <dd className="font-mono text-foreground">{device.edge_url ? device.edge_url.replace(/.*:/, '') : '8008'}</dd>
                        </div>
                        <div className="flex justify-between py-1 border-b border-slate-100">
                          <dt className="text-slate-500">Hardware Platform</dt>
                          <dd className="font-medium text-foreground">{t?.hardware_platform || device.hardware_platform}</dd>
                        </div>
                        <div className="flex justify-between py-1 border-b border-slate-100">
                          <dt className="text-slate-500">OS Environment</dt>
                          <dd className="text-slate-700 truncate max-w-[180px]" title={t?.os_version || 'Embedded'}>{t?.os_version || 'Embedded OS'}</dd>
                        </div>
                        <div className="flex justify-between py-1 border-b border-slate-100">
                          <dt className="text-slate-500">Python Runtime</dt>
                          <dd className="font-mono text-slate-700">{t?.python_version ? `Python ${t.python_version}` : 'Python 3.11+'}</dd>
                        </div>
                        <div className="flex justify-between py-1 border-b border-slate-100">
                          <dt className="text-slate-500">Station Uptime</dt>
                          <dd className="text-slate-700">{formatUptime(t?.uptime_seconds)}</dd>
                        </div>
                        <div className="flex justify-between py-1">
                          <dt className="text-slate-500">SQLite Outbox</dt>
                          <dd className="font-bold tabular-nums text-agri-green">{t?.storage?.unsynced_scans ?? 0} scans queued</dd>
                        </div>
                      </dl>
                    </div>

                    <div className="pt-3 border-t border-border flex items-center justify-between text-[11px] text-slate-500">
                      <span>Attributed Session:</span>
                      <span className="font-medium text-foreground">{t?.active_batch_code || 'Idle (No Batch)'}</span>
                    </div>
                  </div>

                  {/* Column 2: Computer Vision & AI Inference */}
                  <div className="bg-card border border-border rounded-xl p-5 space-y-4 shadow-sm flex flex-col justify-between">
                    <div className="space-y-3.5">
                      <div className="flex items-center gap-2 pb-2.5 border-b border-border">
                        <Camera className="w-4 h-4 text-brand" aria-hidden="true" />
                        <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">2. Vision &amp; Model Pipeline</h3>
                      </div>

                      {/* Camera Stream Snapshot Canvas */}
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between text-xs font-medium text-slate-700">
                          <span>Live Candling Stream Snapshot:</span>
                          <button
                            onClick={() => handleFetchSnapshot(device.device_id)}
                            disabled={isSnapshotLoading || !isOnline}
                            className="text-[11px] text-brand hover:underline flex items-center gap-1 disabled:opacity-50"
                          >
                            <RefreshCw className={`w-3 h-3 ${isSnapshotLoading ? 'animate-spin' : ''}`} aria-hidden="true" />
                            <span>Capture Frame</span>
                          </button>
                        </div>

                        <div className="w-full h-36 bg-slate-900 border border-slate-800 rounded-lg overflow-hidden flex items-center justify-center relative">
                          {currentSnapshot ? (
                            <img
                              src={currentSnapshot}
                              alt="Real-time candling stream capture"
                              className="w-full h-full object-contain"
                            />
                          ) : (
                            <div className="text-center p-3 text-slate-400 text-xs space-y-1">
                              <ImageIcon className="w-6 h-6 mx-auto opacity-50" aria-hidden="true" />
                              <p className="font-medium">DirectShow Stream: {t?.camera?.resolution || '1280x720'}</p>
                              <p className="text-[10px] text-slate-500">Click &ldquo;Capture Frame&rdquo; to pull the latest image</p>
                            </div>
                          )}
                          <span className={`absolute top-2 right-2 text-[10px] px-1.5 py-0.5 rounded font-medium ${
                            t?.camera?.is_mock ? 'bg-amber-500 text-white' : 'bg-emerald-600 text-white'
                          }`}>
                            {t?.camera?.is_mock ? 'Mock Frames' : 'DirectShow'}
                          </span>
                        </div>
                      </div>

                      {/* Vision Hardware & Model Details */}
                      <dl className="space-y-2 text-xs">
                        <div className="flex justify-between py-1 border-b border-slate-100">
                          <dt className="text-slate-500">Active Camera</dt>
                          <dd className="font-medium text-foreground truncate max-w-[180px]">{t?.camera?.identity || 'Camera #0'}</dd>
                        </div>
                        <div className="flex justify-between py-1 border-b border-slate-100">
                          <dt className="text-slate-500">Stream Resolution</dt>
                          <dd className="font-mono text-foreground">{t?.camera?.resolution || '1280x720'} @ {t?.camera?.fps || 30} FPS</dd>
                        </div>
                        <div className="flex justify-between py-1 border-b border-slate-100">
                          <dt className="text-slate-500">Vision Model File</dt>
                          <dd className="font-mono font-medium text-brand truncate max-w-[180px]" title={t?.ai_model?.model_version || device.model_version}>
                            {t?.ai_model?.model_version || device.model_version}
                          </dd>
                        </div>
                        <div className="flex justify-between py-1 border-b border-slate-100">
                          <dt className="text-slate-500">Execution Runtime</dt>
                          <dd className="font-medium text-slate-700">{t?.ai_model?.engine_type || 'ONNX Runtime FP16'}</dd>
                        </div>
                        <div className="flex justify-between py-1">
                          <dt className="text-slate-500">Sort Threshold</dt>
                          <dd className="font-bold tabular-nums text-foreground">{((t?.ai_model?.sort_confidence ?? 0.70) * 100).toFixed(0)}% (Confidence Gate)</dd>
                        </div>
                      </dl>
                    </div>

                    <div className="pt-3 border-t border-border flex items-center justify-between text-[11px] text-slate-500">
                      <span>Model Cache State:</span>
                      <span className="font-semibold text-agri-green">{t?.ai_model?.warmup_complete ? '3 Warmup Passes Ready' : 'Quantized FP16'}</span>
                    </div>
                  </div>

                  {/* Column 3: Physical IoT Rig & Kinematics */}
                  <div className="bg-card border border-border rounded-xl p-5 space-y-4 shadow-sm flex flex-col justify-between">
                    <div className="space-y-3.5">
                      <div className="flex items-center gap-2 pb-2.5 border-b border-border">
                        <Layers className="w-4 h-4 text-brand" aria-hidden="true" />
                        <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">3. IoT Rig &amp; Kinematics</h3>
                      </div>

                      {/* Rig Profile & Serial Ports */}
                      <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 space-y-2 text-xs">
                        <div className="flex items-center justify-between">
                          <span className="text-slate-600 font-medium">Controller Profile:</span>
                          <span className="font-mono font-bold text-brand bg-white px-2 py-0.5 rounded border border-slate-200">
                            {t?.iot_rig?.rig_profile === 'unified_v4' ? 'Unified Rig (v4)' : t?.iot_rig?.rig_profile === 'three_v3' ? 'Three-Board (v3)' : 'Dual-Board (v2)'}
                          </span>
                        </div>

                        <div className="grid grid-cols-3 gap-1.5 text-[11px] pt-1">
                          <div className="bg-white p-1.5 rounded border border-slate-200 text-center">
                            <span className="text-slate-500 block text-[10px]">Stepper</span>
                            <span className="font-mono font-semibold text-slate-800">{t?.iot_rig?.conveyor_port || 'COM5'}</span>
                          </div>
                          <div className="bg-white p-1.5 rounded border border-slate-200 text-center">
                            <span className="text-slate-500 block text-[10px]">Servo</span>
                            <span className="font-mono font-semibold text-slate-800">{t?.iot_rig?.servo_port || 'COM7'}</span>
                          </div>
                          <div className="bg-white p-1.5 rounded border border-slate-200 text-center">
                            <span className="text-slate-500 block text-[10px]">Lamp</span>
                            <span className="font-mono font-semibold text-slate-800">{t?.iot_rig?.light_port || 'COM9'}</span>
                          </div>
                        </div>

                        <div className="text-[11px] text-slate-500 pt-0.5 flex justify-between">
                          <span>Gate Angles:</span>
                          <span className="font-medium text-slate-700">Fertile {t?.iot_rig?.fertile_angle ?? 180}° • Infertile {t?.iot_rig?.infertile_angle ?? 50}°</span>
                        </div>
                      </div>

                      {/* Preserved Kinematics Calibration Sliders */}
                      <div className="p-3.5 bg-slate-50 rounded-lg border border-slate-200 space-y-3">
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-1.5 min-w-0">
                            <Sliders aria-hidden="true" className="w-3.5 h-3.5 text-brand" />
                            <span className="text-xs font-bold text-slate-800">Conveyor Kinematics (&Delta;t = D / v)</span>
                          </div>
                          <span className="text-[11px] font-semibold text-brand bg-maroon-50 px-2 py-0.5 rounded border border-maroon-200">
                            &Delta;t = {calculatedDelayMs} ms delay
                          </span>
                        </div>

                        <div className="space-y-2 text-xs">
                          {/* Speed Slider */}
                          <div>
                            <div className="flex justify-between text-[11px] font-medium text-slate-700 mb-0.5">
                              <span>Conveyor Velocity (v):</span>
                              <span className="font-mono">{cal.speed.toFixed(1)} cm/s</span>
                            </div>
                            <input
                              aria-label={`Conveyor speed for ${device.device_name}`}
                              type="range"
                              disabled={!canCalibrate || savingDeviceId === device.device_id}
                              aria-describedby={!canCalibrate ? `calibration-permission-${device.device_id}` : undefined}
                              min="5"
                              max="25"
                              step="0.5"
                              value={cal.speed}
                              onChange={(e) =>
                                setCalibration(prev => ({
                                  ...prev,
                                  [device.device_id]: { ...cal, speed: Number(e.target.value) }
                                }))
                              }
                              className="w-full min-h-11 accent-[#800000] cursor-pointer disabled:cursor-not-allowed"
                            />
                          </div>

                          {/* Distance Slider */}
                          <div>
                            <div className="flex justify-between text-[11px] font-medium text-slate-700 mb-0.5">
                              <span>Optical Sensor to Diverter Distance (D):</span>
                              <span className="font-mono">{cal.dist.toFixed(1)} cm</span>
                            </div>
                            <input
                              aria-label={`Sensor to chute distance for ${device.device_name}`}
                              type="range"
                              disabled={!canCalibrate || savingDeviceId === device.device_id}
                              aria-describedby={!canCalibrate ? `calibration-permission-${device.device_id}` : undefined}
                              min="10"
                              max="50"
                              step="1"
                              value={cal.dist}
                              onChange={(e) =>
                                setCalibration(prev => ({
                                  ...prev,
                                  [device.device_id]: { ...cal, dist: Number(e.target.value) }
                                }))
                              }
                              className="w-full min-h-11 accent-[#800000] cursor-pointer disabled:cursor-not-allowed"
                            />
                          </div>

                          {/* Servo Pulse Slider */}
                          <div>
                            <div className="flex justify-between text-[11px] font-medium text-slate-700 mb-0.5">
                              <span>ESP32 Ejector Solenoid Pulse:</span>
                              <span className="font-mono">{cal.pulse} ms (Lockout: 600ms)</span>
                            </div>
                            <input
                              aria-label={`Servo pulse duration for ${device.device_name}`}
                              type="range"
                              disabled={!canCalibrate || savingDeviceId === device.device_id}
                              aria-describedby={!canCalibrate ? `calibration-permission-${device.device_id}` : undefined}
                              min="150"
                              max="400"
                              step="10"
                              value={cal.pulse}
                              onChange={(e) =>
                                setCalibration(prev => ({
                                  ...prev,
                                  [device.device_id]: { ...cal, pulse: Number(e.target.value) }
                                }))
                              }
                              className="w-full min-h-11 accent-[#800000] cursor-pointer disabled:cursor-not-allowed"
                            />
                          </div>
                        </div>

                        {!canCalibrate && (
                          <p id={`calibration-permission-${device.device_id}`} className="text-sm text-slate-600">
                            Only administrators and managers can edit calibration records.
                          </p>
                        )}

                        <div className="page-actions justify-end pt-1">
                          <button
                            onClick={() => handleSaveCalibration(device.device_id)}
                            disabled={!canCalibrate || savingDeviceId === device.device_id}
                            className="primary-action text-xs"
                          >
                            <Save aria-hidden="true" className="w-3.5 h-3.5" />
                            <span>{savingDeviceId === device.device_id ? "Saving…" : "Save calibration record"}</span>
                          </button>
                        </div>
                      </div>
                    </div>

                    <div className="pt-3 border-t border-border flex items-center justify-between text-[11px] text-slate-500">
                      <span>Step Velocity:</span>
                      <span className="font-mono text-slate-700">{t?.iot_rig?.stepper_speed_us ?? 3000} &mu;s half-period</span>
                    </div>
                  </div>
                </div>

                {/* Institutional Safety Notice */}
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-xs text-slate-600 flex items-start gap-3">
                  <ShieldCheck className="w-5 h-5 text-brand shrink-0 mt-0.5" aria-hidden="true" />
                  <div>
                    <h4 className="font-semibold text-slate-800">Physical Actuation Safety Lock</h4>
                    <p className="mt-0.5 leading-relaxed">
                      Conveyor travel timing and calibration records configured here are stored centrally. To execute mechanical motor tests, camera realignment, or candling lamp strobe tests, use the physical edge application station. Remote web commands do not trigger unvalidated physical motion.
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
