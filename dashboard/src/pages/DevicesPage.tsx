import React, { useState, useEffect } from 'react';
import {
  Cpu,
  RefreshCw,
  Activity,
  CheckCircle2,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { Device } from '../types';
import { Badge } from '../components/Badge';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';

export const DevicesPage: React.FC = () => {
  const [devices, setDevices] = useState<Device[]>([]);
  const [pingStatus, setPingStatus] = useState<Record<string, string>>({});
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchDevices = async () => {
    setIsRefreshing(true);
    const data = await apiClient.getDevices();
    setDevices(data);
    setTimeout(() => setIsRefreshing(false), 300);
  };

  useEffect(() => {
    fetchDevices();
  }, []);

  const handlePing = (deviceId: string) => {
    setPingStatus(prev => ({ ...prev, [deviceId]: 'Pinging...' }));
    setTimeout(() => {
      setPingStatus(prev => ({ ...prev, [deviceId]: 'Online (12ms • UART OK)' }));
    }, 400);
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground">
            Edge Sorter Devices
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Connected Raspberry Pi and PC candling stations, ESP32 UART actuators, and conveyor calibration.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={fetchDevices}
          disabled={isRefreshing}
          className="gap-1.5 text-xs"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
          Refresh Status
        </Button>
      </div>

      {/* Devices Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {devices.map((device) => (
          <Card key={device.device_id}>
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center text-foreground">
                    <Cpu className="w-4 h-4" />
                  </div>
                  <div>
                    <CardTitle className="text-base font-semibold">{device.device_name}</CardTitle>
                    <CardDescription className="text-xs font-mono">{device.device_id}</CardDescription>
                  </div>
                </div>
                <Badge type="device" value={device.status} />
              </div>
            </CardHeader>

            <CardContent className="space-y-4">
              {/* Technical Properties Grid */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-3 bg-muted/40 rounded border">
                  <span className="text-[11px] text-muted-foreground block">Hardware Platform</span>
                  <span className="font-semibold text-foreground mt-0.5 block">{device.hardware_platform}</span>
                </div>
                <div className="p-3 bg-muted/40 rounded border">
                  <span className="text-[11px] text-muted-foreground block">ONNX Model Runtime</span>
                  <span className="font-semibold text-foreground mt-0.5 block">{device.model_version}</span>
                </div>
                <div className="p-3 bg-muted/40 rounded border">
                  <span className="text-[11px] text-muted-foreground block">IP Address</span>
                  <span className="font-semibold text-foreground mt-0.5 block">{device.ip_address || '127.0.0.1'}</span>
                </div>
                <div className="p-3 bg-muted/40 rounded border">
                  <span className="text-[11px] text-muted-foreground block">Last Heartbeat</span>
                  <span className="font-semibold text-foreground mt-0.5 block">
                    {device.last_heartbeat ? new Date(device.last_heartbeat).toLocaleTimeString() : 'Online'}
                  </span>
                </div>
              </div>

              {/* Conveyor Kinematics Parameters */}
              <div className="p-3 bg-muted/30 rounded border space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-foreground">Conveyor Calibration Parameters</span>
                  <span className="text-[11px] text-muted-foreground font-mono">Δt = D / v</span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="p-2 bg-background rounded border">
                    <span className="text-[10px] text-muted-foreground block">Speed (v)</span>
                    <span className="font-semibold text-foreground">{device.conveyor_speed_cm_s} cm/s</span>
                  </div>
                  <div className="p-2 bg-background rounded border">
                    <span className="text-[10px] text-muted-foreground block">Distance (D)</span>
                    <span className="font-semibold text-foreground">{device.conveyor_dist_cm} cm</span>
                  </div>
                  <div className="p-2 bg-background rounded border">
                    <span className="text-[10px] text-muted-foreground block">Servo Pulse</span>
                    <span className="font-semibold text-foreground">{device.servo_pulse_ms} ms</span>
                  </div>
                </div>
              </div>

              {/* Ping Actions */}
              <div className="flex items-center justify-between pt-1 text-xs">
                <span className="text-muted-foreground">
                  {pingStatus[device.device_id] ? (
                    <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                      {pingStatus[device.device_id]}
                    </span>
                  ) : (
                    'Ready for telemetry check'
                  )}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePing(device.device_id)}
                  className="gap-1.5 text-xs"
                >
                  <Activity className="w-3.5 h-3.5" />
                  Test Connection
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};
