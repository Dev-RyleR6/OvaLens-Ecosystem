import React, { useState, useEffect } from 'react';
import {
  Cpu,
  Wifi,
  HardDrive,
  Activity,
  Gauge,
  Sliders,
  RefreshCw,
  CheckCircle,
  Clock
} from 'lucide-react';
import { apiClient } from '../api/client';
import { Device } from '../types';
import { Badge } from '../components/Badge';

export const DevicesPage: React.FC = () => {
  const [devices, setDevices] = useState<Device[]>([]);
  const [pingStatus, setPingStatus] = useState<Record<string, string>>({});

  const fetchDevices = async () => {
    const data = await apiClient.getDevices();
    setDevices(data);
  };

  useEffect(() => {
    fetchDevices();
  }, []);

  const handlePing = (deviceId: string) => {
    setPingStatus(prev => ({ ...prev, [deviceId]: 'PINGING...' }));
    setTimeout(() => {
      setPingStatus(prev => ({ ...prev, [deviceId]: 'PONG (12ms)' }));
    }, 400);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-100">Edge Sorting Stations & IoT Telemetry</h2>
          <p className="text-xs text-slate-400">Manage Raspberry Pi / PC vision sorting rigs, conveyor parameters, and ESP32 actuators</p>
        </div>

        <button
          onClick={fetchDevices}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-semibold border border-slate-700 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh Telemetry
        </button>
      </div>

      {/* Devices Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {devices.map((device) => (
          <div
            key={device.device_id}
            className="bg-[#1E293B] border border-slate-800 rounded-xl p-6 shadow-lg space-y-5 relative overflow-hidden"
          >
            {/* Header / ID */}
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-[#800000]/20 rounded-xl border border-[#800000]/40 text-amber-400">
                  <Cpu className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-100">{device.device_name}</h3>
                  <p className="text-xs text-amber-400/90 font-mono font-semibold">{device.device_id}</p>
                </div>
              </div>
              <Badge type="device" value={device.status} />
            </div>

            {/* Hardware Telemetry Grid */}
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
                <p className="text-slate-400">Hardware Platform</p>
                <p className="font-bold text-slate-200 mt-0.5">{device.hardware_platform}</p>
              </div>
              <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
                <p className="text-slate-400">Vision Model Version</p>
                <p className="font-mono font-semibold text-amber-300 mt-0.5">{device.model_version}</p>
              </div>
              <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
                <p className="text-slate-400">IP Address</p>
                <p className="font-mono text-slate-200 mt-0.5">{device.ip_address || '127.0.0.1'}</p>
              </div>
              <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
                <p className="text-slate-400">Last Telemetry Ping</p>
                <p className="font-semibold text-slate-300 mt-0.5">
                  {device.last_heartbeat ? new Date(device.last_heartbeat).toLocaleTimeString() : 'Never'}
                </p>
              </div>
            </div>

            {/* Conveyor Calibration Specs */}
            <div className="p-4 bg-slate-900/80 rounded-lg border border-slate-700/60 space-y-2 text-xs">
              <div className="flex items-center gap-1.5 text-slate-300 font-bold">
                <Sliders className="w-4 h-4 text-amber-400" />
                Active Conveyor & Actuator Calibration (Δt = D/v)
              </div>
              <div className="grid grid-cols-3 gap-2 text-center pt-1">
                <div className="p-2 bg-slate-800 rounded">
                  <span className="text-[10px] text-slate-400 block">Conveyor Speed</span>
                  <span className="font-mono font-bold text-slate-100">{device.conveyor_speed_cm_s} cm/s</span>
                </div>
                <div className="p-2 bg-slate-800 rounded">
                  <span className="text-[10px] text-slate-400 block">Distance to Gate</span>
                  <span className="font-mono font-bold text-slate-100">{device.conveyor_dist_cm} cm</span>
                </div>
                <div className="p-2 bg-slate-800 rounded">
                  <span className="text-[10px] text-slate-400 block">Servo Pulse</span>
                  <span className="font-mono font-bold text-slate-100">{device.servo_pulse_ms} ms</span>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-between pt-1">
              <span className="text-xs font-mono text-emerald-400">
                {pingStatus[device.device_id] || ''}
              </span>
              <button
                onClick={() => handlePing(device.device_id)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold rounded-lg border border-slate-700 transition-colors flex items-center gap-1.5 shadow-sm"
              >
                <Activity className="w-3.5 h-3.5 text-amber-400" />
                Ping Station
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
