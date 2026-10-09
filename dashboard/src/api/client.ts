import type { ScanPage, ScanSearchParams } from '../types';
import axios from 'axios';
import {
  Batch,
  BatchSummary,
  EggScan,
  Device,
  AnalyticsOverview,
  EconomicYield,
  CandlingSession,
  MortalityTrends,
  BreedMetricItem,
  BatchStage,
  User,
  AuditLog,
  HatcherySettings,
  ModelCheckpoint,
  TrainingLossEpoch,
  ModelOpsSummary,
  FertilityClass,
  PenoySalvageRecord,
  HistoricalRecordSummary,
  LoginCredentials,
  AuthResponse,
  BatchForecastResponse,
} from '../types';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 8000,
});

// Auto-attach JWT Bearer Token from localStorage
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('ovalens_auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auto-handle 401 Unauthorized / Token Expiration
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('ovalens_auth_token');
      localStorage.removeItem('ovalens_user');
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export const apiClient = {
  // Authentication & Security
  login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
    const res = await api.post<AuthResponse>('/auth/login', credentials);
    if (res.data?.access_token) {
      localStorage.setItem('ovalens_auth_token', res.data.access_token);
      localStorage.setItem('ovalens_user', JSON.stringify(res.data.user));
    }
    return res.data;
  },

  getMe: async (): Promise<User> => {
    const res = await api.get<User>('/auth/me');
    return res.data;
  },

  logout: () => {
    localStorage.removeItem('ovalens_auth_token');
    localStorage.removeItem('ovalens_user');
  },

  checkHealth: async (): Promise<boolean> => {
    try {
      const res = await api.get('/health');
      return res.data?.status === 'healthy';
    } catch {
      return false;
    }
  },

  // Analytics
  getOverview: async (): Promise<AnalyticsOverview> => {
    const res = await api.get<AnalyticsOverview>('/analytics/overview');
    return res.data;
  },

  getEconomicYield: async (params?: { batch_id?: string; breed?: string; status?: string }): Promise<EconomicYield> => {
    const res = await api.get<EconomicYield>('/analytics/economic-yield', { params });
    return res.data;
  },

  getMortalityTrends: async (): Promise<MortalityTrends> => {
    const res = await api.get<MortalityTrends>('/analytics/mortality-trends');
    return res.data;
  },

  getBreedComparison: async (): Promise<BreedMetricItem[]> => {
    const res = await api.get<{ breeds: BreedMetricItem[] }>('/analytics/breed-comparison');
    return res.data?.breeds || [];
  },

  // Batches
  getAllBatches: async (): Promise<BatchSummary[]> => {
    const batches: BatchSummary[] = [];
    for (let offset = 0; ; offset += 200) {
      const res = await api.get<BatchSummary[]>('/batches', { params: { limit: 200, offset } });
      batches.push(...res.data);
      if (res.data.length < 200) return batches;
    }
  },

  getBatches: async (): Promise<BatchSummary[]> => {
    const res = await api.get<BatchSummary[]>('/batches');
    return res.data;
  },

  getBatch: async (batchId: string): Promise<BatchSummary> => {
    const res = await api.get<BatchSummary>(`/batches/${batchId}`);
    return res.data;
  },

  createBatch: async (data: Partial<Batch>): Promise<Batch> => {
    const res = await api.post<Batch>('/batches', data);
    return res.data;
  },

  advanceBatchStage: async (batchId: string, nextStage: BatchStage): Promise<BatchSummary> => {
    const res = await api.post<BatchSummary>(`/batches/${batchId}/advance-stage`, { stage: nextStage });
    return res.data;
  },

  getBatchAnalytics: async (batchId: string): Promise<any> => {
    const res = await api.get(`/batches/${batchId}/analytics`);
    return res.data;
  },

  getBatchForecast: async (batchId: string): Promise<BatchForecastResponse> => {
    const res = await api.get<BatchForecastResponse>(`/batches/${batchId}/forecast`);
    return res.data;
  },

  finalizeBatchHatch: async (batchId: string, payload: { hatched_count: number; unhatched_count?: number; notes?: string }): Promise<BatchSummary> => {
    const res = await api.post<BatchSummary>(`/batches/${batchId}/finalize-hatch`, payload);
    return res.data;
  },

  checkBatchMilestones: async (): Promise<any> => {
    const res = await api.post('/batches/check-milestones');
    return res.data;
  },

  deleteBatch: async (batchId: string): Promise<void> => {
    await api.delete(`/batches/${batchId}`);
  },

  getMortalityProgression: async (): Promise<any> => {
    const res = await api.get('/analytics/mortality-progression');
    return res.data;
  },

  // Sessions
  getSessions: async (batchId?: string): Promise<CandlingSession[]> => {
    const sessions: CandlingSession[] = [];
    for (let offset = 0; ; offset += 200) {
      const res = await api.get<CandlingSession[]>('/sessions', { params: { batch_id: batchId, limit: 200, offset } });
      sessions.push(...res.data);
      if (res.data.length < 200) return sessions;
    }
  },

  // Scans
  getScans: async (params?: { batch_id?: string; final_class?: string; limit?: number }): Promise<EggScan[]> => {
    const res = await api.get<EggScan[]>('/scans', { params });
    return res.data;
  },

  searchScans: async (params: ScanSearchParams, signal?: AbortSignal): Promise<ScanPage> => {
    const res = await api.get<ScanPage>('/scans/search', { params, signal });
    return res.data;
  },

  overrideScanClassification: async (scanId: string, newClass: FertilityClass, reason?: string): Promise<EggScan> => {
    const res = await api.patch<EggScan>(`/scans/${scanId}/override`, { final_class: newClass, reason });
    return res.data;
  },

  // Devices
  getDevices: async (): Promise<Device[]> => {
    const res = await api.get<Device[]>('/devices');
    return res.data;
  },

  updateDeviceCalibration: async (deviceId: string, data: Partial<Device>): Promise<Device> => {
    const res = await api.patch<Device>(`/devices/${deviceId}`, data);
    return res.data;
  },

  // User Management
  getUsers: async (): Promise<User[]> => {
    const res = await api.get<User[]>('/users');
    return res.data;
  },

  createUser: async (user: Partial<User> & { password?: string }): Promise<User> => {
    const res = await api.post<User>('/users', user);
    return res.data;
  },

  toggleUserStatus: async (userId: string): Promise<User> => {
    const res = await api.patch<User>(`/users/${userId}/status`);
    return res.data;
  },

  // Audit Logs
  getAuditLogs: async (params?: { action?: string; limit?: number }): Promise<AuditLog[]> => {
    const res = await api.get<AuditLog[]>('/audit-logs', { params });
    return res.data;
  },

  // User Profile & Account Management
  updateMyProfile: async (fullName: string): Promise<User> => {
    const res = await api.patch<User>('/users/me/profile', { full_name: fullName });
    return res.data;
  },

  changeMyPassword: async (currentPassword: string, newPassword: string): Promise<{ status: string; message: string }> => {
    const res = await api.patch<{ status: string; message: string }>('/users/me/password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    return res.data;
  },

  // Hatchery Settings & Backups
  getSettings: async (): Promise<any> => {
    const res = await api.get('/settings');
    return res.data;
  },

  updateSettings: async (settings: any): Promise<any> => {
    const res = await api.put('/settings', settings);
    return res.data;
  },

  getBackups: async (): Promise<any> => {
    const res = await api.get('/settings/backups');
    return res.data;
  },

  createBackup: async (): Promise<any> => {
    const res = await api.post('/settings/backups/create');
    return res.data;
  },

  downloadBackup: async (filename: string): Promise<Blob> => {
    const res = await api.get<Blob>(`/settings/backups/${encodeURIComponent(filename)}/download`, { responseType: 'blob' });
    return res.data;
  },

  downloadBackupUrl: (filename: string) => `/api/v1/settings/backups/${encodeURIComponent(filename)}/download`,

  // Reports
  downloadCSVUrl: (batchId: string) => `/api/v1/reports/batch/${batchId}/csv`,
  downloadPDFUrl: (batchId: string) => `/api/v1/reports/batch/${batchId}/pdf`,

  // MLOps & Model Metrics
  getModelOpsSummary: async (): Promise<ModelOpsSummary> => {
    return {
      active_model_version: 'yolov8n-fp16-v1.2.onnx',
      total_training_images: 4800,
      dataset_distribution: {
        fertile: 3200,
        infertile: 1600,
      },
      overall_map50: 0.958,
      overall_precision: 0.942,
      overall_recall: 0.961,
      avg_latency_ms: 24.6,
      confusion_matrix: {
        classes: ['FERTILE', 'INFERTILE'],
        matrix: [
          [0.96, 0.04],
          [0.05, 0.95],
        ],
        raw_counts: [
          [480, 20],
          [25, 475],
        ],
      },
    };
  },

  getModelCheckpoints: async (): Promise<ModelCheckpoint[]> => {
    return [
      {
        model_id: 'mdl-onnx-v1.2',
        version_tag: 'yolov8n-fp16-v1.2.onnx',
        format: 'ONNX_FP16',
        architecture: 'YOLOv8 Nano (Candling Customized)',
        file_size_mb: 6.2,
        map50: 0.958,
        map50_95: 0.784,
        precision: 0.942,
        recall: 0.961,
        avg_latency_ms: 24.6,
        is_active: true,
        deployed_stations: ['STATION-01-RP5', 'STATION-02-PC'],
        created_at: new Date(Date.now() - 7 * 86400000).toISOString(),
      },
      {
        model_id: 'mdl-onnx-v1.1',
        version_tag: 'yolov8s-fp16-v1.1.onnx',
        format: 'ONNX_FP16',
        architecture: 'YOLOv8 Small (High Capacity)',
        file_size_mb: 22.4,
        map50: 0.964,
        map50_95: 0.798,
        precision: 0.951,
        recall: 0.968,
        avg_latency_ms: 38.2,
        is_active: false,
        deployed_stations: [],
        created_at: new Date(Date.now() - 21 * 86400000).toISOString(),
      },
    ];
  },

  getTrainingLoss: async (): Promise<TrainingLossEpoch[]> => {
    return [
      { epoch: 10, train_box_loss: 0.142, val_box_loss: 0.158, train_cls_loss: 0.198, val_cls_loss: 0.21, map50: 0.62 },
      { epoch: 20, train_box_loss: 0.112, val_box_loss: 0.128, train_cls_loss: 0.154, val_cls_loss: 0.165, map50: 0.78 },
      { epoch: 30, train_box_loss: 0.089, val_box_loss: 0.098, train_cls_loss: 0.118, val_cls_loss: 0.129, map50: 0.88 },
      { epoch: 40, train_box_loss: 0.071, val_box_loss: 0.079, train_cls_loss: 0.091, val_cls_loss: 0.099, map50: 0.93 },
      { epoch: 50, train_box_loss: 0.058, val_box_loss: 0.065, train_cls_loss: 0.072, val_cls_loss: 0.078, map50: 0.958 },
    ];
  },

  deployModelCheckpoint: async (modelId: string): Promise<ModelCheckpoint> => {
    return {
      model_id: modelId,
      version_tag: `${modelId}.onnx`,
      format: 'ONNX_FP16',
      architecture: 'YOLOv8 Nano (Candling Customized)',
      file_size_mb: 6.2,
      map50: 0.958,
      map50_95: 0.784,
      precision: 0.942,
      recall: 0.961,
      avg_latency_ms: 24.6,
      is_active: true,
      deployed_stations: ['STATION-01-RP5', 'STATION-02-PC'],
      created_at: new Date().toISOString(),
    };
  },
};

export default apiClient;
