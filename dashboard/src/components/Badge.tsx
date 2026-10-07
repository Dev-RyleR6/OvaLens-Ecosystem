import type { FertilityClass, BatchStage, BatchStatus, DeviceStatus } from '../types';

interface BadgeProps {
  type?: 'fertility' | 'stage' | 'status' | 'device' | 'role';
  value: FertilityClass | BatchStage | BatchStatus | DeviceStatus | string;
  size?: 'sm' | 'md';
}

export const Badge = ({ type = 'status', value, size = 'md' }: BadgeProps) => {
  const labels: Record<string, string> = type === 'stage' ? {
    SETTING: 'Day 0 (Setting)', DAY_10: 'Day 10 (Candling)', HATCHED: 'Day 28 (Hatched)', COMPLETED: 'Completed',
  } : {
    FERTILE: 'Fertile', INFERTILE: 'Infertile', MANUAL_REVIEW: 'Awaiting review',
    ONLINE: 'App online', SCANNING: 'Scanning', OFFLINE: 'Offline', ERROR: 'Error',
    STALE: 'Offline (heartbeat expired)', UNKNOWN: 'Status unknown',
    INCUBATING: 'Incubating', CANDLING_DUE: 'Candling due', 'CANDLING DUE': 'Candling due',
    'HATCH DUE': 'Hatch due', COMPLETED: 'Completed', ARCHIVED: 'Archived',
    ADMIN: 'Administrator', MANAGER: 'Manager', OPERATOR: 'Operator',
    ACTIVE: 'Active', INACTIVE: 'Suspended', OVERRIDDEN: 'Corrected',
  };
  const tone = value === 'FERTILE' || value === 'ONLINE' || value === 'SCANNING' || value === 'HATCHED' || value === 'COMPLETED' || value === 'ACTIVE'
    ? 'status-success'
    : value === 'INFERTILE' || value === 'ERROR' ? 'status-danger'
    : ['DAY_10', 'CANDLING_DUE', 'CANDLING DUE', 'HATCH DUE', 'MANUAL_REVIEW'].includes(value) ? 'status-warning'
    : value === 'INCUBATING' || value === 'ADMIN' ? 'status-brand' : 'status-neutral';
  return <span className={`status-badge ${tone} ${size === 'sm' ? 'status-small' : ''}`}>{labels[value] ?? value.replace(/_/g, ' ')}</span>;
};
