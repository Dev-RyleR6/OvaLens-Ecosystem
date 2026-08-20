import React from 'react';
import { FertilityClass, BatchStage, BatchStatus, DeviceStatus } from '../types';
import { Badge as UiBadge } from './ui/badge';

interface BadgeProps {
  type?: 'fertility' | 'stage' | 'status' | 'device';
  value: FertilityClass | BatchStage | BatchStatus | DeviceStatus | string;
  size?: 'sm' | 'md';
}

export const Badge: React.FC<BadgeProps> = ({ type = 'status', value }) => {
  if (type === 'fertility') {
    switch (value) {
      case 'FERTILE':
        return <UiBadge variant="success">Fertile</UiBadge>;
      case 'INFERTILE':
        return <UiBadge variant="warning">Infertile (Penoy)</UiBadge>;
      case 'ABNORMAL':
        return <UiBadge variant="destructive">Abnormal</UiBadge>;
      default:
        return <UiBadge variant="secondary">{value}</UiBadge>;
    }
  }

  if (type === 'stage') {
    switch (value) {
      case 'SETTING':
        return <UiBadge variant="outline">Setting (Day 0)</UiBadge>;
      case 'DAY_10':
        return <UiBadge variant="warning">Day 10 (1st Candle)</UiBadge>;
      case 'DAY_18':
        return <UiBadge variant="secondary">Day 18 (Transfer)</UiBadge>;
      case 'DAY_25':
        return <UiBadge variant="secondary">Day 25 (Pipping)</UiBadge>;
      case 'HATCHED':
      case 'COMPLETED':
        return <UiBadge variant="success">Hatched (Day 28)</UiBadge>;
      default:
        return <UiBadge variant="outline">{value}</UiBadge>;
    }
  }

  if (type === 'device') {
    if (value === 'ONLINE') {
      return <UiBadge variant="success">Online</UiBadge>;
    }
    return <UiBadge variant="secondary">Offline</UiBadge>;
  }

  if (value === 'INCUBATING') {
    return <UiBadge variant="maroon">Incubating</UiBadge>;
  }
  if (value === 'COMPLETED') {
    return <UiBadge variant="success">Completed</UiBadge>;
  }

  return <UiBadge variant="outline">{value}</UiBadge>;
};
