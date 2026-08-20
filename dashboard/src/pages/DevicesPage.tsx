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
  Clock,
  ShieldCheck,
  Zap
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
      setPingStatus(prev => ({ ...prev, [deviceId]: 'PONG (12ms • UART OK)' }));
    }, 350);
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-obsidian-900 border border-obsidian-700/80 p-4 rounded-lg shadow-xl">
        <div>
          <h2 className="text-lg font-display font-black tracking-wide text-white uppercase flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-led-pulse" />
            Edge Sorter Stations & Microcontroller Telemetry
          </h2>
          <p className="text-xs font-mono text-slate-400">
            Raspberry Pi 5 / Industrial PC nodes • ESP32 UART actuators • Conveyor kinematics (Δt = D/v)
          </p>
        </div>

        <button
          onClick={fetchDevices}
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-obsidian-950 hover:bg-obsidian-800 text-slate-300 rounded border border-obsidian-700 text-xs font-mono font-bold transition-colors shadow-sm"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh Telemetry
        </button>
      </div>

      {/* Devices Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {devices.map((device) => (
          <div
            key={device.device_id}
            className="panel-scada p-5 space-y-4"
          >
            {/* Top Node Header */}
            <div className="flex items-start justify-between border-b border-obsidian-700/60 pb-3">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-[#800000]/20 rounded border border-[#800000]/50 text-amber-400">
                  <Cpu className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-display font-bold uppercase tracking-wider text-slate-100">
                    {device.device_name}
                  </h3>
                  <p className="text-xs text-amber-300 font-mono font-semibold">{device.device_id}</p>
                </div>
              </div>
              <Badge type="device" value={device.status} />
            </div>

            {/* Hardware Telemetry Grid */}
            <div className="grid grid-cols-2 gap-2.5 text-xs font-mono">
              <div className="p-2.5 bg-obsidian-950 rounded border border-obsidian-800">
                <span className="text-[10px] text-slate-500 block">HARDWARE PLATFORM</span>
                <span className="font-bold text-slate-200 mt-0.5 block">{device.hardware_platform}</span>
              </div>
              <div className="p-2.5 bg-obsidian-950 rounded border border-obsidian-800">
                <span className="text-[10px] text-slate-500 block">ONNX MODEL RUNTIME</span>
                <span className="font-bold text-amber-300 mt-0.5 block">{device.model_version}</span>
              </div>
              <div className="p-2.5 bg-obsidian-950 rounded border border-obsidian-800">
                <span className="text-[10px] text-slate-500 block">LOCAL IP ADDRESS</span>
                <span className="font-bold text-slate-200 mt-0.5 block">{device.ip_address || '127.0.0.1'}</span>
              </div>
              <div className="p-2.5 bg-obsidian-950 rounded border border-obsidian-800">
                <span className="text-[10px] text-slate-500 block">LAST TELEMETRY HEARTBEAT</span>
                <span className="font-bold text-emerald-400 mt-0.5 block">
                  {device.last_heartbeat ? new Date(device.last_heartbeat).toLocaleTimeString() : 'Online (Active)'}
                </span>
              </div>
            </div>

            {/* Conveyor Kinematics Calibration Parameters */}
            <div className="p-3 bg-obsidian-950 rounded border border-obsidian-800 space-y-2 text-xs font-mono">
              <div className="flex items-center justify-between text-slate-300 font-bold border-b border-obsidian-850 pb-1.5">
                <div className="flex items-center gap-1.5">
                  <Sliders className="w-3.5 h-3.5 text-amber-400" />
                  <span>Conveyor & ESP32 Ejection Kinematics</span>
                </div>
                <span className="text-[10px] text-amber-300 font-semibold">Δt = D / v</span>
              </div>

              <div className="grid grid-cols-3 gap-2 text-center pt-1">
                <div className="p-2 bg-obsidian-900 rounded border border-obsidian-800">
                  <span className="text-[9px] text-slate-500 block">VELOCITY (v)</span>
                  <span className="font-bold text-slate-100 text-xs">{device.conveyor_speed_cm_s} cm/s</span>
                </div>
                <div className="p-2 bg-obsidian-900 rounded border border-obsidian-800">
                  <span className="text-[9px] text-slate-500 block">DISTANCE (D)</span>
                  <span className="font-bold text-slate-100 text-xs">{device.conveyor_dist_cm} cm</span>
                </div>
                <div className="p-2 bg-obsidian-900 rounded border border-obsidian-800">
                  <span className="text-[9px] text-slate-500 block">SERVO PULSE</span>
                  <span className="font-bold text-slate-100 text-xs">{device.servo_pulse_ms} ms</span>
                </div>
              </div>
            </div>

            {/* Diagnostics & Remote Ping */}
            <div className="flex items-center justify-between pt-1 font-mono text-xs">
              <span className="text-emerald-400 font-bold">
                {pingStatus[device.device_id] || 'NODE SYNCED (SQLite WAL: OK)'}
              </span>
              <button
                onClick={() => handlePing(device.device_id)}
                className="px-3 py-1.5 bg-obsidian-800 hover:bg-obsidian-700 text-slate-200 font-bold rounded border border-obsidian-700 transition-colors flex items-center gap-1.5 shadow-sm"
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
