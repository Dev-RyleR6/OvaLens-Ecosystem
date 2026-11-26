import { useCallback, useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { Camera, Radio, RefreshCw, RotateCcw } from 'lucide-react';
import { apiClient } from '../api/client';
import { Badge } from '../components/Badge';
import { DataUnavailableState } from '../components/ui/DataUnavailableState';
import { EmptyState } from '../components/ui/EmptyState';
import { useAuth } from '../context/AuthContext';
import { deviceAvailability } from '../lib/deviceStatus';
import type { Device } from '../types';
import './DevicesPage.css';

type Availability = ReturnType<typeof deviceAvailability>;
type Calibration = { speed: number; distance: number; pulse: number };
type Feedback = { tone: 'success' | 'warning' | 'danger'; text: string };

const stationStatus: Record<Availability, string> = {
  ONLINE: 'App online',
  SCANNING: 'Scanning',
  OFFLINE: 'Offline',
  ERROR: 'Error',
  STALE: 'Heartbeat expired',
  UNKNOWN: 'Status unknown',
};

const rigNames: Record<string, string> = {
  unified_v4: 'Single-ESP32 Unified (v4)',
  three_v3: 'Three-board (v3)',
  dual_v2: 'Dual-board (v2)',
};

const isOnline = (status: Availability) => status === 'ONLINE' || status === 'SCANNING';

function Fact({ label, children }: { label: string; children?: ReactNode }) {
  return (
    <div className="sorter-fact">
      <dt>{label}</dt>
      <dd>{children ?? <span className="sorter-muted">Not reported</span>}</dd>
    </div>
  );
}

function readCalibration(device: Device): Calibration {
  return {
    speed: device.conveyor_speed_cm_s,
    distance: device.conveyor_dist_cm,
    pulse: device.servo_pulse_ms,
  };
}

function formatUptime(seconds?: number) {
  if (seconds == null) return undefined;
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return hours ? `${hours}h ${minutes}m` : `${minutes}m`;
}

function formatRelativeAge(iso?: string, now = Date.now()) {
  if (!iso) return undefined;
  const ts = Date.parse(iso);
  if (!Number.isFinite(ts)) return undefined;
  const diffSec = Math.max(0, Math.round((now - ts) / 1000));
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  return `${Math.floor(diffHr / 24)}d ago`;
}

function formatPort(port?: string, status?: string) {
  return [port, status?.toLowerCase().replace(/_/g, ' ')].filter(Boolean).join(' · ') || undefined;
}

function measurement(value: number | undefined, unit: string) {
  return value == null ? undefined : `${value} ${unit}`;
}

function DeviceDiagnostics({ device }: { device: Device }) {
  const telemetry = device.telemetry;
  const model = telemetry?.ai_model;
  const rig = telemetry?.iot_rig;
  const profile = rig?.rig_profile;
  const portStatus = rig?.ports_status;

  return (
    <div className="sorter-diagnostics-grid">
      <div className="sorter-spec-group">
        <h4>Station &amp; network</h4>
        <dl>
          <Fact label="Hostname">{telemetry?.hostname || undefined}</Fact>
          <Fact label="IP address">{device.ip_address || undefined}</Fact>
          <Fact label="Edge endpoint">{device.edge_url || undefined}</Fact>
          <Fact label="Platform">{telemetry?.hardware_platform || device.hardware_platform || undefined}</Fact>
          <Fact label="Operating system">{telemetry?.os_version || undefined}</Fact>
          <Fact label="Python version">{telemetry?.python_version || undefined}</Fact>
          <Fact label="Uptime">{formatUptime(telemetry?.uptime_seconds)}</Fact>
        </dl>
      </div>

      <div className="sorter-spec-group">
        <h4>Vision pipeline</h4>
        <dl>
          <Fact label="Model">{model?.model_version || device.model_version || undefined}</Fact>
          <Fact label="Runtime">{model?.engine_type || undefined}</Fact>
          <Fact label="Sort threshold">{model?.sort_confidence == null ? undefined : `${(model.sort_confidence * 100).toFixed(0)}%`}</Fact>
          <Fact label="Warmup">{model?.warmup_complete == null ? undefined : model.warmup_complete ? 'Complete' : 'Incomplete'}</Fact>
        </dl>
      </div>

      <div className="sorter-spec-group">
        <h4>Controller &amp; I/O</h4>
        <dl>
          <Fact label="Rig profile">{profile ? rigNames[profile] ?? profile : undefined}</Fact>
          {profile === 'unified_v4' ? (
            <Fact label="Unified Serial Bus (UNIFIED_V3)">{formatPort(rig?.conveyor_port, portStatus?.conveyor)}</Fact>
          ) : (
            <>
              <Fact label="Conveyor port">{formatPort(rig?.conveyor_port, portStatus?.conveyor)}</Fact>
              <Fact label={profile === 'three_v3' ? 'Servo / sensor port' : 'Servo port'}>{formatPort(rig?.servo_port, portStatus?.servo)}</Fact>
              {profile === 'three_v3' && <Fact label="Lamp port">{formatPort(rig?.light_port, portStatus?.light)}</Fact>}
            </>
          )}
          {rig?.board_state?.fault && <Fact label="Board fault"><span className="sorter-alert-text">{rig.board_state.fault}</span></Fact>}
          <Fact label="Fertile angle">{rig?.fertile_angle == null ? undefined : `${rig.fertile_angle}°`}</Fact>
          <Fact label="Neutral angle">{rig?.neutral_angle == null ? undefined : `${rig.neutral_angle}°`}</Fact>
          <Fact label="Infertile angle">{rig?.infertile_angle == null ? undefined : `${rig.infertile_angle}°`}</Fact>
          {profile === 'unified_v4' && (
            <>
              <Fact label="Stepper / sleep">GPIO 16 / 4 / 17</Fact>
              <Fact label="Gate servo">GPIO 32</Fact>
              <Fact label="IR sensor · Lamp">GPIO 26 · GPIO 27</Fact>
            </>
          )}
        </dl>
      </div>

      <div className="sorter-spec-group">
        <h4>Stepper &amp; capture timing</h4>
        <dl>
          <Fact label="Holder spacing">{measurement(rig?.holder_steps, 'steps')}</Fact>
          <Fact label="Sorter offset">{measurement(rig?.sorter_steps, 'steps')}</Fact>
          <Fact label="Settle time">{measurement(rig?.settle_ms, 'ms')}</Fact>
          <Fact label="Hold time">{measurement(rig?.hold_ms, 'ms')}</Fact>
          <Fact label="Step half-period">{measurement(rig?.stepper_speed_us, 'µs')}</Fact>
          {profile && rigNames[profile] && <Fact label="Optical lockout">600 ms</Fact>}
        </dl>
      </div>
    </div>
  );
}

export function DevicesPage() {
  const { user } = useAuth();
  const canCalibrate = user?.role === 'ADMIN' || user?.role === 'MANAGER';
  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState('');
  const [isRefreshing, setIsRefreshing] = useState(true);
  const [isError, setIsError] = useState(false);
  const [now, setNow] = useState(Date.now);
  const [drafts, setDrafts] = useState<Record<string, Calibration | undefined>>({});
  const [savingDeviceId, setSavingDeviceId] = useState<string | null>(null);
  const [probingDeviceId, setProbingDeviceId] = useState<string | null>(null);
  const [probeFeedback, setProbeFeedback] = useState<Record<string, Feedback | undefined>>({});
  const [saveFeedback, setSaveFeedback] = useState<Record<string, Feedback | undefined>>({});
  const [snapshots, setSnapshots] = useState<Record<string, { url: string; captured: string }>>({});
  const [loadingSnapshot, setLoadingSnapshot] = useState<Record<string, boolean>>({});
  const [snapshotError, setSnapshotError] = useState<Record<string, boolean>>({});
  const snapshotUrls = useRef(new Map<string, string>());
  const mounted = useRef(false);

  const fetchDevices = useCallback(async (background = false) => {
    if (!background) setIsRefreshing(true);
    try {
      const list = await apiClient.getDevices();
      setDevices(list);
      setSelectedDeviceId(previous => list.some(device => device.device_id === previous)
        ? previous
        : list[0]?.device_id ?? '');
      setNow(Date.now());
      setIsError(false);
    } catch {
      setIsError(true);
    } finally {
      if (!background) setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    void fetchDevices();
    const poll = setInterval(() => { void fetchDevices(true); }, 15_000);
    const timer = setInterval(() => setNow(Date.now()), 30_000);
    const urls = snapshotUrls.current;
    return () => {
      mounted.current = false;
      clearInterval(timer);
      clearInterval(poll);
      urls.forEach(url => URL.revokeObjectURL(url));
      urls.clear();
    };
  }, [fetchDevices]);

  const checkConnection = async (deviceId: string) => {
    setProbingDeviceId(deviceId);
    setProbeFeedback(previous => ({ ...previous, [deviceId]: undefined }));
    try {
      const result = await apiClient.getDeviceLive(deviceId);
      setProbeFeedback(previous => ({
        ...previous,
        [deviceId]: result.is_live
          ? { tone: 'success', text: 'The edge app responded to the connection check.' }
          : { tone: 'warning', text: 'The edge app did not respond. Showing its last recorded data.' },
      }));
      if (result.is_live && result.device) {
        setDevices(previous => previous.map(device => device.device_id === deviceId
          ? { ...device, ...result.device, telemetry: result.telemetry }
          : device));
        setNow(Date.now());
      }
    } catch {
      setProbeFeedback(previous => ({
        ...previous,
        [deviceId]: { tone: 'danger', text: 'Connection check failed. Try again.' },
      }));
    } finally {
      setProbingDeviceId(null);
    }
  };

  const captureSnapshot = async (deviceId: string) => {
    setLoadingSnapshot(previous => ({ ...previous, [deviceId]: true }));
    setSnapshotError(previous => ({ ...previous, [deviceId]: false }));
    try {
      const url = await apiClient.getDeviceCameraSnapshot(deviceId);
      if (!mounted.current) {
        if (url) URL.revokeObjectURL(url);
        return;
      }
      if (!url) {
        setSnapshotError(previous => ({ ...previous, [deviceId]: true }));
        return;
      }

      const oldUrl = snapshotUrls.current.get(deviceId);
      if (oldUrl) URL.revokeObjectURL(oldUrl);
      snapshotUrls.current.set(deviceId, url);
      setSnapshots(previous => ({ ...previous, [deviceId]: { url, captured: new Date().toISOString() } }));
    } catch {
      setSnapshotError(previous => ({ ...previous, [deviceId]: true }));
    } finally {
      setLoadingSnapshot(previous => ({ ...previous, [deviceId]: false }));
    }
  };

  const saveCalibration = async (deviceId: string, calibration: Calibration) => {
    setSavingDeviceId(deviceId);
    setSaveFeedback(previous => ({ ...previous, [deviceId]: undefined }));
    try {
      const saved = await apiClient.updateDeviceCalibration(deviceId, {
        conveyor_speed_cm_s: calibration.speed,
        conveyor_dist_cm: calibration.distance,
        servo_pulse_ms: calibration.pulse,
      });
      setDevices(previous => previous.map(device => device.device_id === deviceId
        ? {
          ...device,
          conveyor_speed_cm_s: saved.conveyor_speed_cm_s,
          conveyor_dist_cm: saved.conveyor_dist_cm,
          servo_pulse_ms: saved.servo_pulse_ms,
        }
        : device));
      setDrafts(previous => ({ ...previous, [deviceId]: undefined }));
      setSaveFeedback(previous => ({
        ...previous,
        [deviceId]: { tone: 'success', text: 'Calibration record saved.' },
      }));
    } catch {
      setSaveFeedback(previous => ({
        ...previous,
        [deviceId]: { tone: 'danger', text: 'Could not save calibration. Your edits are still here. Try again.' },
      }));
    } finally {
      setSavingDeviceId(null);
    }
  };

  const device = devices.find(item => item.device_id === selectedDeviceId) ?? devices[0];
  const onlineCount = devices.filter(item => isOnline(deviceAvailability(item, now))).length;

  const renderStation = () => {
    if (!device) {
      if (isError) {
        return (
          <DataUnavailableState
            title="Device records unavailable"
            description="The dashboard could not load registered stations."
            onRetry={() => fetchDevices()}
            isRetrying={isRefreshing}
          />
        );
      }
      if (isRefreshing) return <p role="status" className="sorter-loading">Loading device records…</p>;
      return <EmptyState title="No sorter devices registered" description="Registered edge stations will appear here." />;
    }

    const id = device.device_id;
    const status = deviceAvailability(device, now);
    const online = isOnline(status);
    const storedCalibration = readCalibration(device);
    const calibration = drafts[id] ?? storedCalibration;
    const hasUnsavedCalibration = Boolean(drafts[id]) && (
      calibration.speed !== storedCalibration.speed
      || calibration.distance !== storedCalibration.distance
      || calibration.pulse !== storedCalibration.pulse
    );
    const delay = calibration.speed > 0 ? Math.round(calibration.distance / calibration.speed * 1000) : undefined;
    const permissionId = 'sorter-calibration-permission';
    const telemetry = device.telemetry;
    const camera = telemetry?.camera;
    const cameraInfo = [camera?.identity, camera?.resolution, camera?.fps ? `${camera.fps} fps` : null, camera?.is_mock ? 'Simulated camera' : null].filter(Boolean).join(' · ');
    const heartbeat = device.last_heartbeat && Number.isFinite(Date.parse(device.last_heartbeat)) ? device.last_heartbeat : undefined;
    const heartbeatAge = formatRelativeAge(heartbeat, now);
    const unsyncedScans = telemetry?.storage?.unsynced_scans;
    const snapshot = snapshots[id];
    const probe = probeFeedback[id];
    const saveResult = saveFeedback[id];
    const boardState = telemetry?.iot_rig?.board_state;

    function updateCalibration(field: keyof Calibration, value: number) {
      setDrafts(previous => ({ ...previous, [id]: { ...(previous[id] ?? calibration), [field]: value } }));
      setSaveFeedback(previous => ({ ...previous, [id]: undefined }));
    }

    return (
      <div className="sorter-workbench">
        <aside className="sorter-roster" aria-labelledby="sorter-roster-title">
          <div className="sorter-roster-heading">
            <h2 id="sorter-roster-title">Stations</h2>
            <span className="sorter-roster-count">{onlineCount}/{devices.length} online</span>
          </div>
          <ul className="sorter-roster-list">
            {devices.map(item => {
              const availability = deviceAvailability(item, now);
              const age = formatRelativeAge(item.last_heartbeat, now);
              return (
                <li key={item.device_id}>
                  <button
                    type="button"
                    className="sorter-station"
                    aria-pressed={id === item.device_id}
                    onClick={() => setSelectedDeviceId(item.device_id)}
                  >
                    <span className="sorter-station-row">
                      <span aria-hidden="true" className="sorter-status-dot" data-status={availability} />
                      <span className="sorter-station-name">{item.device_name}</span>
                    </span>
                    <span className="sorter-station-meta">
                      <span>{item.device_id}</span>
                      <span>{stationStatus[availability]}{age ? ` · ${age}` : ''}</span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
          <label className="sorter-roster-select">
            <span className="sr-only">Select station</span>
            <select value={id} onChange={event => setSelectedDeviceId(event.target.value)}>
              {devices.map(item => <option key={item.device_id} value={item.device_id}>{item.device_name}</option>)}
            </select>
          </label>
        </aside>

        <section key={id} className="sorter-inspector" aria-labelledby="sorter-station-title">
          <header className="sorter-inspector-header">
            <div className="min-w-0">
              <div className="sorter-station-title">
                <h2 id="sorter-station-title">{device.device_name}</h2>
                <Badge type="device" value={status} />
              </div>
              <p className="sorter-identifier">
                <span>{id}</span>
                {telemetry?.hardware_platform || device.hardware_platform ? (
                  <>
                    <span aria-hidden="true">·</span>
                    <span>{telemetry?.hardware_platform || device.hardware_platform}</span>
                  </>
                ) : null}
                {telemetry?.uptime_seconds != null && (
                  <>
                    <span aria-hidden="true">·</span>
                    <span>Uptime {formatUptime(telemetry.uptime_seconds)}</span>
                  </>
                )}
              </p>
            </div>
            <button type="button" className="secondary-action" onClick={() => void checkConnection(id)} disabled={probingDeviceId !== null}>
              <Radio aria-hidden="true" />
              {probingDeviceId === id ? 'Checking…' : 'Check connection'}
            </button>
          </header>

          {probe && (
            <p role={probe.tone === 'danger' ? 'alert' : 'status'} className="sorter-feedback" data-tone={probe.tone}>{probe.text}</p>
          )}

          <div className="sorter-overview">
            <section className="sorter-camera" aria-labelledby="sorter-camera-title">
              <div className="sorter-section-heading">
                <div>
                  <h3 id="sorter-camera-title">Camera snapshot</h3>
                  {cameraInfo && <p className="sorter-camera-spec">{cameraInfo}</p>}
                </div>
                <button type="button" className="secondary-action" onClick={() => void captureSnapshot(id)} disabled={loadingSnapshot[id] || !online}>
                  <Camera aria-hidden="true" />
                  {loadingSnapshot[id] ? 'Capturing…' : snapshot ? 'Retake snapshot' : 'Capture snapshot'}
                </button>
              </div>
              <figure>
                <div className="sorter-camera-frame" data-captured={Boolean(snapshot)} aria-busy={loadingSnapshot[id] || undefined}>
                  {snapshot ? (
                    <img src={snapshot.url} alt={`Candling camera snapshot from ${device.device_name}`} />
                  ) : (
                    <div className="sorter-camera-placeholder">
                      <Camera size={22} strokeWidth={1.75} aria-hidden="true" />
                      <p className="sorter-camera-state">
                        {loadingSnapshot[id] ? 'Capturing snapshot…' : online ? 'No snapshot captured' : 'Camera unavailable'}
                      </p>
                      <p className="sorter-muted">
                        {online
                          ? 'Capture a frame to inspect candling illumination and egg cradle framing.'
                          : 'The station must be online to request a snapshot from the edge camera.'}
                      </p>
                    </div>
                  )}
                </div>
                {snapshot && (
                  <figcaption className="sorter-camera-caption">
                    <span>Latest frame from {camera?.identity || 'edge camera'}</span>
                    <time dateTime={snapshot.captured}>Captured at {new Date(snapshot.captured).toLocaleTimeString()}</time>
                  </figcaption>
                )}
              </figure>
              {snapshotError[id] && <p role="alert" className="sorter-feedback" data-tone="danger">Could not capture a snapshot. Check the connection and try again.</p>}
            </section>

            <section className="sorter-activity" aria-labelledby="sorter-activity-title">
              <h3 id="sorter-activity-title">Station activity</h3>
              <dl>
                <Fact label="Last heartbeat">
                  {heartbeat && (
                    <span className="sorter-heartbeat-value">
                      <time dateTime={heartbeat}>{new Date(heartbeat).toLocaleString('en-PH', { dateStyle: 'medium', timeStyle: 'short' })}</time>
                      {heartbeatAge && <span className="sorter-muted">({heartbeatAge})</span>}
                    </span>
                  )}
                </Fact>
                <Fact label="Active batch">{telemetry?.active_batch_code === undefined ? undefined : telemetry.active_batch_code || 'No active batch'}</Fact>
                <Fact label="Current operator">{telemetry?.active_operator === undefined ? undefined : telemetry.active_operator || 'Unassigned'}</Fact>
                <Fact label="Scans awaiting sync">
                  {unsyncedScans == null ? undefined : (
                    <span className={unsyncedScans > 0 ? 'sorter-sync-pending' : undefined}>
                      {unsyncedScans.toLocaleString()}
                    </span>
                  )}
                </Fact>
                <Fact label="Local buffer">{telemetry?.storage?.mode ? telemetry.storage.mode : undefined}</Fact>
                <Fact label="Vision model">{telemetry?.ai_model?.model_version || device.model_version || undefined}</Fact>
                {boardState && (
                  <Fact label="Controller state">
                    {boardState.fault && boardState.fault !== 'NONE'
                      ? <span className="sorter-alert-text">{boardState.fault}</span>
                      : [boardState.busy === '1' ? 'Busy' : 'Idle', boardState.light === '1' ? 'Lamp on' : 'Lamp off'].join(' · ')}
                  </Fact>
                )}
              </dl>
            </section>
          </div>

          <section className="sorter-section" aria-labelledby="sorter-diagnostics-title">
            <div className="sorter-section-bar">
              <h3 id="sorter-diagnostics-title">Hardware &amp; model telemetry</h3>
              {telemetry && !online && <span className="sorter-muted">Last reported values</span>}
            </div>
            <DeviceDiagnostics device={device} />
          </section>

          <section className="sorter-section" aria-labelledby="sorter-calibration-title">
            <div className="sorter-section-bar">
              <div>
                <h3 id="sorter-calibration-title">Conveyor calibration</h3>
                <p className="sorter-muted">Saved to the backend record. Apply and test physical motion in the edge app.</p>
              </div>
              {hasUnsavedCalibration && <span className="status-badge status-warning status-small">Unsaved edits</span>}
            </div>

            <form className="sorter-calibration" onSubmit={event => {
              event.preventDefault();
              if (canCalibrate && savingDeviceId === null) void saveCalibration(id, calibration);
            }}>
              <div className="sorter-calibration-fields">
                <label className="sorter-slider-field">
                  <span className="sorter-slider-header">
                    <span>Conveyor speed</span>
                    <span className="sorter-calibration-value">{calibration.speed.toFixed(1)} cm/s</span>
                  </span>
                  <input
                    type="range" min="5" max="25" step="0.5"
                    value={calibration.speed}
                    aria-label="Conveyor speed"
                    aria-valuetext={`${calibration.speed} centimeters per second`}
                    aria-describedby={!canCalibrate ? permissionId : undefined}
                    disabled={!canCalibrate || savingDeviceId === id}
                    onChange={event => updateCalibration('speed', event.target.valueAsNumber)}
                  />
                  <span className="sorter-slider-bounds" aria-hidden="true">
                    <span>5 cm/s</span>
                    <span>25 cm/s</span>
                  </span>
                </label>

                <label className="sorter-slider-field">
                  <span className="sorter-slider-header">
                    <span>Sensor to diverter distance</span>
                    <span className="sorter-calibration-value">{calibration.distance.toFixed(1)} cm</span>
                  </span>
                  <input
                    type="range" min="10" max="50" step="1"
                    value={calibration.distance}
                    aria-label="Sensor to diverter distance"
                    aria-valuetext={`${calibration.distance} centimeters`}
                    aria-describedby={!canCalibrate ? permissionId : undefined}
                    disabled={!canCalibrate || savingDeviceId === id}
                    onChange={event => updateCalibration('distance', event.target.valueAsNumber)}
                  />
                  <span className="sorter-slider-bounds" aria-hidden="true">
                    <span>10 cm</span>
                    <span>50 cm</span>
                  </span>
                </label>

                <label className="sorter-slider-field">
                  <span className="sorter-slider-header">
                    <span>Servo pulse duration</span>
                    <span className="sorter-calibration-value">{calibration.pulse} ms</span>
                  </span>
                  <input
                    type="range" min="150" max="400" step="10"
                    value={calibration.pulse}
                    aria-label="Servo pulse duration"
                    aria-valuetext={`${calibration.pulse} milliseconds`}
                    aria-describedby={!canCalibrate ? permissionId : undefined}
                    disabled={!canCalibrate || savingDeviceId === id}
                    onChange={event => updateCalibration('pulse', event.target.valueAsNumber)}
                  />
                  <span className="sorter-slider-bounds" aria-hidden="true">
                    <span>150 ms</span>
                    <span>400 ms</span>
                  </span>
                </label>
              </div>

              <div className="sorter-calibration-footer">
                <div className="sorter-delay-readout">
                  <span>Estimated travel delay</span>
                  <strong>{measurement(delay, 'ms') ?? '—'}</strong>
                </div>
                <div className="page-actions">
                  {hasUnsavedCalibration && (
                    <button
                      type="button"
                      className="secondary-action"
                      disabled={savingDeviceId !== null}
                      onClick={() => {
                        setDrafts(previous => ({ ...previous, [id]: undefined }));
                        setSaveFeedback(previous => ({ ...previous, [id]: undefined }));
                      }}
                    >
                      <RotateCcw aria-hidden="true" />
                      Reset
                    </button>
                  )}
                  <button type="submit" className="primary-action" disabled={!canCalibrate || savingDeviceId !== null}>
                    {savingDeviceId === id ? 'Saving…' : 'Save calibration record'}
                  </button>
                </div>
              </div>

              {!canCalibrate && <p id={permissionId} className="sorter-muted">Only administrators and managers can edit calibration records.</p>}
              {saveResult && (
                <p role={saveResult.tone === 'danger' ? 'alert' : 'status'} className="sorter-feedback" data-tone={saveResult.tone}>{saveResult.text}</p>
              )}
            </form>
          </section>
        </section>
      </div>
    );
  };

  return (
    <div className="sorter-devices" aria-busy={isRefreshing}>
      <header className="page-header">
        <div>
          <h1>Sorter devices</h1>
          <p className="page-description">Live edge station status, camera inspection, controller telemetry, and conveyor timing records.</p>
        </div>
        <div className="page-actions">
          <button type="button" className="secondary-action" onClick={() => void fetchDevices()} disabled={isRefreshing}>
            <RefreshCw className={isRefreshing ? 'animate-spin' : undefined} aria-hidden="true" />
            {isRefreshing ? 'Refreshing…' : 'Refresh stations'}
          </button>
        </div>
      </header>
      {isError && device && <p role="alert" className="feedback-warning">Could not refresh stations. Showing the last loaded records.</p>}
      {renderStation()}
    </div>
  );
}
