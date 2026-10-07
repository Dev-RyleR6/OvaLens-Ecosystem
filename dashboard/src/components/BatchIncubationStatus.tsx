import type { BatchSummary } from '../types';
import { Badge } from './Badge';

const stageLabels = { SETTING: 'Day 0 setting', DAY_10: 'Day 10 candling', HATCHED: 'Day 28 hatched', COMPLETED: 'Completed' };

export function BatchIncubationStatus({ batch }: { batch: BatchSummary }) {
  const finished = ['COMPLETED', 'ARCHIVED'].includes(batch.status) || batch.current_stage === 'COMPLETED';
  const status = finished ? (batch.status === 'ARCHIVED' ? 'ARCHIVED' : 'COMPLETED') : batch.milestone_alert?.split(':')[0] || batch.status;
  return <div className="batch-stage" title={batch.milestone_alert || undefined}>
    <Badge type="status" value={status} />
    {!finished && <span className="batch-stage-description">{stageLabels[batch.current_stage]}</span>}
  </div>;
}
