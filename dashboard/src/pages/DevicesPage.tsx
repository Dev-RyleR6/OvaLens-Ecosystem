import { useAuth } from '../context/AuthContext';
import { deviceAvailability } from '../lib/deviceStatus';
import React, { useState, useEffect } from 'react';
import {
  Cpu,
  RefreshCw,
  Sliders,
  CheckCircle2,
  Radio,
  Save,
  Camera,
  Microscope,
  Zap,
  Play,
  Lightbulb,
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
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isError, setIsError] = useState(false);
  const [savingDeviceId, setSavingDeviceId] = useState<string | null>(null);
  const [now, setNow] = useState(Date.now);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  // Calibration state per device
  const [calibration, setCalibration] = useState<Record<string, { speed: number; dist: number; pulse: number }>>({});

  const fetchDevices = async (background = false) => {
    setIsRefreshing(true);
    setIsError(false);
    try {
      const data = await apiClient.getDevices();
      setDevices(data || []);
      setNow(Date.now());

      const calMap: Record<string, { speed: number; dist: number; pulse: number }> = {};
      (data || []).forEach(d => {
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
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    void fetchDevices();
    const poll = setInterval(() => { void fetchDevices(true); }, 15_000);
    const timer = setInterval(() => setNow(Date.now()), 30_000);
    return () => { clearInterval(timer); clearInterval(poll); };
  }, []);

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

  return (
    <div className="space-y-6 pb-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-foreground tracking-tight">
            Sorter devices
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Check the latest sorter heartbeat and saved calibration records.
          </p>
        </div>

        <button
          onClick={() => { void fetchDevices(); }}
          disabled={isRefreshing}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-card border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-semibold  transition-colors cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
          <span>Refresh Edge Hardware</span>
        </button>
      </div>

      {saveMessage && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs font-semibold text-emerald-800 flex items-center gap-2 ">
          <CheckCircle2 className="w-4 h-4 text-emerald-700 flex-shrink-0" />
          <span>{saveMessage}</span>
        </div>
      )}

      {saveError && <div role="alert" className="p-4 border border-red-300 rounded-xl bg-red-50 text-red-800">{saveError}</div>}
      {isError && devices.length > 0 && <p role="alert" className="text-amber-800">Refresh failed. Previously loaded device records are shown.</p>}
      {/* Edge Devices Grid */}
      {isError && devices.length === 0 ? (
        <DataUnavailableState
          title="Edge Stations Offline"
          description="Unable to connect to edge sorting hardware records in PostgreSQL. Ensure the backend REST service is reachable."
          onRetry={fetchDevices}
          isRetrying={isRefreshing}
        />
      ) : !isRefreshing && devices.length === 0 ? (
        <EmptyState
          title="No Sorter Stations Registered"
          description="No edge sorting machines (ESP32 / Raspberry Pi) have registered with the central backend yet."
        />
      ) : (
        <div className="grid grid-cols-1 2xl:grid-cols-2 gap-6">
        {devices.map((device) => {
          const cal = calibration[device.device_id] || {
            speed: device.conveyor_speed_cm_s || 12.5,
            dist: device.conveyor_dist_cm || 25.0,
            pulse: device.servo_pulse_ms || 250,
          };

          const calculatedDelayMs = Math.round((cal.dist / cal.speed) * 1000);

          return (
            <div
              key={device.device_id}
              className="bg-card border border-border rounded-xl p-5  space-y-4  transition-all"
            >
              {/* Device Header with Live Radar Beacon */}
              <div className="flex flex-wrap items-start justify-between gap-3 pb-3 border-b border-slate-100">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="relative">
                    <div className="w-10 h-10 rounded-lg bg-maroon-50 text-brand border border-maroon-200 flex items-center justify-center font-bold">
                      <Cpu className="w-5 h-5" />
                    </div>
                    {['ONLINE', 'SCANNING'].includes(deviceAvailability(device)) && (
                      <span className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-emerald-600 " />
                    )}
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-foreground">{device.device_name}</h3>
                    <span className="text-[11px] text-slate-500 font-mono">{device.device_id} • IP: {device.ip_address || 'Not reported'}</span>
                  </div>
                </div>
                <Badge type="device" value={deviceAvailability(device, now)} />
              </div>

              <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                <div><dt className="text-slate-500">Platform</dt><dd>{device.hardware_platform || 'Not reported'}</dd></div>
                <div><dt className="text-slate-500">Model version</dt><dd className="break-all">{device.model_version || 'Not reported'}</dd></div>
                <div className="sm:col-span-2"><dt className="text-slate-500">Last heartbeat</dt><dd>{device.last_heartbeat ? new Date(device.last_heartbeat).toLocaleString('en-PH') : 'No heartbeat recorded'}</dd></div>
              </dl>

              {/* Interactive Conveyor Kinematics Calibration Box */}
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <Sliders className="w-4 h-4 text-brand" />
                    <span className="text-xs font-bold text-slate-800">Conveyor Travel Kinematics (Δt = D / v)</span>
                  </div>
                  <span className="text-xs font-semibold text-brand bg-maroon-50 px-2 py-0.5 rounded border border-maroon-200">
                    Δt = {calculatedDelayMs} ms delay
                  </span>
                </div>

                <div className="space-y-2.5 text-xs">
                  {/* Speed Slider */}
                  <div>
                    <div className="flex justify-between text-[11px] font-semibold text-slate-700 mb-1">
                      <span>Conveyor Velocity (v):</span>
                      <span>{cal.speed.toFixed(1)} cm/s</span>
                    </div>
                    <input
                      aria-label={`Conveyor speed for ${device.device_name}`}
                      type="range"
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
                      className="w-full accent-[#800000] cursor-pointer"
                    />
                  </div>

                  {/* Distance Slider */}
                  <div>
                    <div className="flex justify-between text-[11px] font-semibold text-slate-700 mb-1">
                      <span>Optical Sensor to Diverter Distance (D):</span>
                      <span>{cal.dist.toFixed(1)} cm</span>
                    </div>
                    <input
                      aria-label={`Sensor to chute distance for ${device.device_name}`}
                      type="range"
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
                      className="w-full accent-[#800000] cursor-pointer"
                    />
                  </div>

                  {/* Servo Pulse Slider */}
                  <div>
                    <div className="flex justify-between text-[11px] font-semibold text-slate-700 mb-1">
                      <span>ESP32 Ejector Solenoid Pulse:</span>
                      <span>{cal.pulse} ms (Lockout: 600ms)</span>
                    </div>
                    <input
                      aria-label={`Servo pulse duration for ${device.device_name}`}
                      type="range"
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
                      className="w-full accent-[#800000] cursor-pointer"
                    />
                  </div>
                </div>

                <div className="pt-2 flex items-center justify-end">
                  <button
                    onClick={() => handleSaveCalibration(device.device_id)}
                    disabled={!canCalibrate || savingDeviceId === device.device_id}
                    className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-[#800000] hover:bg-[#6B0000] text-white text-xs font-bold  transition-colors cursor-pointer disabled:opacity-50"
                  >
                    <Save className="w-3.5 h-3.5" />
                    <span>{savingDeviceId === device.device_id ? "Saving…" : "Save calibration record"}</span>
                  </button>
                </div>
              </div>

              <div className="border-t border-slate-200 pt-3 text-slate-600">
                <p className="font-medium text-slate-800">Hardware tests</p>
                <p className="mt-1">Run actuator, light, and sensor tests from the edge application. Remote tests are unavailable in this dashboard.</p>
              </div>
            </div>
          );
        })}
        </div>
      )}
    </div>
  );
};
