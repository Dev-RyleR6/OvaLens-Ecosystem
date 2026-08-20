export type DuckBreed = 'KAYUMANGGI' | 'ITIM' | 'KHAKI';
export type BatchStage = 'SETTING' | 'DAY_10' | 'DAY_18' | 'DAY_25' | 'HATCHED' | 'COMPLETED';
export type BatchStatus = 'INCUBATING' | 'COMPLETED' | 'CANCELLED';
export type FertilityClass = 'FERTILE' | 'INFERTILE' | 'ABNORMAL';
export type RoutingAction = 'ACCEPT' | 'REJECT';
export type DeviceStatus = 'ONLINE' | 'OFFLINE' | 'MAINTENANCE';
export type UserRole = 'ADMIN' | 'MANAGER' | 'OPERATOR';

export interface User {
  user_id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface Batch {
  batch_id: string;
  batch_code: string;
  breed: DuckBreed;
  incubator_id: string;
  initial_egg_count: number;
  set_date: string;
  target_hatch_date: string;
  current_stage: BatchStage;
  status: BatchStatus;
  hatched_count: number;
  unhatched_count: number;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface BatchSummary extends Batch {
  total_scanned: number;
  fertile_count: number;
  infertile_count: number;
  abnormal_count: number;
  fertility_rate: number;
  hatchability_rate: number;
}

export interface CandlingSession {
  session_id: string;
  batch_id: string;
  device_id: string;
  stage: 'DAY_10' | 'DAY_18' | 'DAY_25';
  operator_name: string;
  started_at: string;
  ended_at?: string;
  total_scanned: number;
  fertile_count: number;
  infertile_count: number;
  abnormal_count: number;
  avg_inference_ms: number;
  created_at: string;
}

export interface EggScan {
  scan_id: string;
  session_id: string;
  batch_id: string;
  sequence_number: number;
  final_class: FertilityClass;
  confidence: number;
  inference_ms: number;
  routing_action: RoutingAction;
  thumbnail_url?: string;
  detections: Array<{
    bbox: number[];
    confidence: number;
    class: string;
  }>;
  scanned_at: string;
}

export interface Device {
  device_id: string;
  device_name: string;
  ip_address?: string;
  hardware_platform: string;
  model_version: string;
  status: DeviceStatus;
  last_heartbeat?: string;
  conveyor_speed_cm_s: number;
  conveyor_dist_cm: number;
  servo_pulse_ms: number;
  created_at: string;
}

export interface AnalyticsOverview {
  total_eggs_scanned: number;
  total_fertile: number;
  total_infertile: number;
  total_abnormal: number;
  overall_fertility_rate: number;
  active_batches_count: number;
  avg_inference_ms: number;
}

export interface EconomicYield {
  penoy_culled_day_10: number;
  penoy_unit_price_php: number;
  salvage_revenue_php: number;
  incubator_energy_saved_kwh: number;
  energy_savings_php: number;
  total_economic_benefit_php: number;
  duckling_sales_projected_php?: number;
}

export interface MortalityTrends {
  day_10_early_mortality_rate: number;
  day_18_mid_mortality_rate: number;
  day_25_late_mortality_rate: number;
  total_culled_eggs: number;
}

export interface BreedMetricItem {
  breed: string;
  total_eggs: number;
  fertile_count: number;
  infertile_count: number;
  abnormal_count: number;
  fertility_rate: number;
  hatched_count: number;
  hatchability_rate: number;
}

export interface AuditLog {
  log_id: number;
  user_id?: string;
  operator_name?: string;
  action: string;
  entity_type: string;
  entity_id: string;
  details: Record<string, any>;
  ip_address?: string;
  severity: 'INFO' | 'WARNING' | 'SECURITY';
  created_at: string;
}

export interface HatcherySettings {
  facility_name: string;
  institution: string;
  location: string;
  min_confidence_threshold: number;
  aspect_ratio_min: number;
  aspect_ratio_max: number;
  hsv_luminance_min: number;
  penoy_unit_price: number;
  duckling_unit_price: number;
  kwh_rate_php: number;
  sqlite_retention_days: number;
  optical_debounce_ms: number;
}

export interface ModelCheckpoint {
  model_id: string;
  version_tag: string;
  format: 'ONNX_FP16' | 'ONNX_FP32' | 'PYTORCH_PT';
  architecture: string;
  file_size_mb: number;
  map50: number;
  map50_95: number;
  precision: number;
  recall: number;
  avg_latency_ms: number;
  is_active: boolean;
  deployed_stations: string[];
  created_at: string;
}

export interface TrainingLossEpoch {
  epoch: number;
  train_box_loss: number;
  val_box_loss: number;
  train_cls_loss: number;
  val_cls_loss: number;
  map50: number;
}

export interface ModelOpsSummary {
  active_model_version: string;
  total_training_images: number;
  dataset_distribution: {
    fertile: number;
    infertile: number;
    abnormal: number;
  };
  overall_map50: number;
  overall_precision: number;
  overall_recall: number;
  avg_latency_ms: number;
  confusion_matrix: {
    classes: string[];
    matrix: number[][]; // 3x3 normalized percentage [ [96.4, 2.1, 1.5], [3.2, 94.8, 2.0], [4.2, 3.7, 92.1] ]
    raw_counts: number[][];
  };
}
