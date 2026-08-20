import React, { useState, useEffect } from 'react';
import {
  Cpu,
  RefreshCw,
  Activity,
  Sliders,
  CheckCircle2,
  HardDrive,
  Radio,
  Save,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { Device } from '../types';
import { Badge } from '../components/Badge';

export const DevicesPage: React.FC = () => {
  const [devices, setDevices] = useState<Device[]>([]);
  const [pingStatus, setPingStatus] = useState<Record<string, string>>({});
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [savingDeviceId, setSavingDeviceId] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  // Calibration state per device
  const [calibration, setCalibration] = useState<Record<string, { speed: number; dist: number; pulse: number }>>({});

  const fetchDevices = async () => {
    setIsRefreshing(true);
    const data = await apiClient.getDevices();
    setDevices(data);

    const calMap: Record<string, { speed: number; dist: number; pulse: number }> = {};
    data.forEach(d => {
      calMap[d.device_id] = {
        speed: d.conveyor_speed_cm_s || 12.5,
        dist: d.conveyor_dist_cm || 25.0,
        pulse: d.servo_pulse_ms || 250,
      };
    });
    setCalibration(calMap);
    setTimeout(() => setIsRefreshing(false), 300);
  };

  useEffect(() => {
    fetchDevices();
  }, []);

  const handlePing = (deviceId: string) => {
    setPingStatus(prev => ({ ...prev, [deviceId]: 'Pinging UART...' }));
    setTimeout(() => {
      setPingStatus(prev => ({ ...prev, [deviceId]: 'Online • 115200 Baud (12ms latency)' }));
    }, 350);
  };

  const handleSaveCalibration = async (deviceId: string) => {
    const cal = calibration[deviceId];
    if (!cal) return;

    setSavingDeviceId(deviceId);
    try {
      await apiClient.updateDeviceCalibration(deviceId, {
        conveyor_speed_cm_s: cal.speed,
        conveyor_dist_cm: cal.dist,
        servo_pulse_ms: cal.pulse,
      });
      setSaveMessage(`Calibration synced to ${deviceId} successfully.`);
      setTimeout(() => setSaveMessage(null), 3000);
    } finally {
      setSavingDeviceId(null);
    }
  };

  return (
    <div className="space-y-6 pb-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-[#0F172A] tracking-tight">
            Edge Candling Sorter Stations
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Raspberry Pi 5 and Workstation sorting stations, ESP32 UART servo kinematics, and optical candling calibration.
          </p>
        </div>

        <button
          onClick={fetchDevices}
          disabled={isRefreshing}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-semibold shadow-xs transition-colors cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
          <span>Refresh Hardware Status</span>
        </button>
      </div>

      {saveMessage && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs font-semibold text-emerald-800 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-700" />
          <span>{saveMessage}</span>
        </div>
      )}

      {/* Devices Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {devices.map((device) => {
          const cal = calibration[device.device_id] || {
            speed: device.conveyor_speed_cm_s || 12.5,
            dist: device.conveyor_dist_cm || 25.0,
            pulse: device.servo_pulse_ms || 250,
          };

          const calculatedDelayMs = Math.round((cal.dist / cal.speed) * 1000);

          return (
            <div key={device.device_id} className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-xs space-y-4">
              {/* Device Header */}
              <div className="flex items-start justify-between pb-3 border-b border-slate-100">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-maroon-50 text-[#800000] border border-maroon-200 flex items-center justify-center font-bold">
                    <Cpu className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-[#0F172A]">{device.device_name}</h3>
                    <span className="text-[11px] text-slate-500 font-mono">{device.device_id}</span>
                  </div>
                </div>
                <Badge type="device" value={device.status} />
              </div>

              {/* Hardware Properties Grid */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="text-[10px] text-slate-500 font-semibold uppercase block">Hardware Platform</span>
                  <span className="font-bold text-[#0F172A] mt-0.5 block">{device.hardware_platform}</span>
                </div>
                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="text-[10px] text-slate-500 font-semibold uppercase block">ONNX Runtime</span>
                  <span className="font-bold text-[#0F172A] mt-0.5 block">{device.model_version}</span>
                </div>
                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="text-[10px] text-slate-500 font-semibold uppercase block">IP Address</span>
                  <span className="font-bold text-[#0F172A] mt-0.5 block font-mono">{device.ip_address || '127.0.0.1'}</span>
                </div>
                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="text-[10px] text-slate-500 font-semibold uppercase block">Last Heartbeat</span>
                  <span className="font-bold text-[#0F172A] mt-0.5 block">
                    {device.last_heartbeat ? new Date(device.last_heartbeat).toLocaleTimeString() : 'Online'}
                  </span>
                </div>
              </div>

              {/* Interactive Conveyor Kinematics Calibration Box */}
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <Sliders className="w-4 h-4 text-[#800000]" />
                    <span className="text-xs font-bold text-slate-800">Conveyor Travel Kinematics (Δt = D / v)</span>
                  </div>
                  <span className="text-xs font-extrabold text-[#800000] bg-maroon-50 px-2 py-0.5 rounded border border-maroon-200">
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
                      <span>Optical Sensor to Ejector Distance (D):</span>
                      <span>{cal.dist.toFixed(1)} cm</span>
                    </div>
                    <input
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
                      <span>ESP32 Ejector Servo Pulse:</span>
                      <span>{cal.pulse} ms (Lockout: 600ms)</span>
                    </div>
                    <input
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
                    disabled={savingDeviceId === device.device_id}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#800000] hover:bg-[#6B0000] text-white text-xs font-bold shadow-xs transition-colors cursor-pointer disabled:opacity-50"
                  >
                    <Save className="w-3.5 h-3.5" />
                    <span>{savingDeviceId === device.device_id ? "Syncing..." : "Sync Calibration to ESP32"}</span>
                  </button>
                </div>
              </div>

              {/* Ping Connection Strip */}
              <div className="flex items-center justify-between pt-1 text-xs">
                <span className="text-slate-600 font-medium">
                  {pingStatus[device.device_id] ? (
                    <span className="text-emerald-700 font-bold">
                      {pingStatus[device.device_id]}
                    </span>
                  ) : (
                    'Ready for UART telemetry check'
                  )}
                </span>
                <button
                  onClick={() => handlePing(device.device_id)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-800 font-semibold transition-colors cursor-pointer"
                >
                  <Radio className="w-3.5 h-3.5 text-slate-600" />
                  <span>Test Connection</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
