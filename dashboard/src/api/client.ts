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
} from '../types';
import {
  mockOverview,
  mockEconomicYield,
  mockBatches,
  mockDevices,
  mockScans,
  mockSessions,
  mockMortalityTrends,
  mockBreedComparison,
} from './mockData';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 4000,
});

export const apiClient = {
  // Analytics
  getOverview: async (): Promise<AnalyticsOverview> => {
    try {
      const res = await api.get<AnalyticsOverview>('/analytics/overview');
      return res.data;
    } catch {
      return mockOverview;
    }
  },

  getEconomicYield: async (): Promise<EconomicYield> => {
    try {
      const res = await api.get<EconomicYield>('/analytics/economic-yield');
      return res.data;
    } catch {
      return mockEconomicYield;
    }
  },

  getMortalityTrends: async (): Promise<MortalityTrends> => {
    try {
      const res = await api.get<MortalityTrends>('/analytics/mortality-trends');
      return res.data;
    } catch {
      return mockMortalityTrends;
    }
  },

  getBreedComparison: async (): Promise<BreedMetricItem[]> => {
    try {
      const res = await api.get<{ breeds: BreedMetricItem[] }>('/analytics/breed-comparison');
      return res.data.breeds;
    } catch {
      return mockBreedComparison;
    }
  },

  // Batches
  getBatches: async (): Promise<BatchSummary[]> => {
    try {
      const res = await api.get<BatchSummary[]>('/batches');
      return res.data;
    } catch {
      return mockBatches;
    }
  },

  getBatch: async (batchId: string): Promise<BatchSummary> => {
    try {
      const res = await api.get<BatchSummary>(`/batches/${batchId}`);
      return res.data;
    } catch {
      const found = mockBatches.find(b => b.batch_id === batchId);
      if (!found) throw new Error("Batch not found");
      return found;
    }
  },

  createBatch: async (data: Partial<Batch>): Promise<Batch> => {
    try {
      const res = await api.post<Batch>('/batches', data);
      return res.data;
    } catch {
      const newBatch: BatchSummary = {
        batch_id: data.batch_code || `BATCH-${Date.now()}`,
        batch_code: data.batch_code || `BATCH-${Date.now()}`,
        breed: data.breed || 'KAYUMANGGI',
        incubator_id: data.incubator_id || 'INCUBATOR-A1',
        initial_egg_count: data.initial_egg_count || 500,
        set_date: data.set_date || new Date().toISOString(),
        target_hatch_date: new Date(Date.now() + 28 * 86400000).toISOString(),
        current_stage: 'SETTING',
        status: 'INCUBATING',
        hatched_count: 0,
        unhatched_count: 0,
        total_scanned: 0,
        fertile_count: 0,
        infertile_count: 0,
        abnormal_count: 0,
        fertility_rate: 0,
        hatchability_rate: 0,
        notes: data.notes,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      mockBatches.unshift(newBatch);
      return newBatch;
    }
  },

  advanceBatchStage: async (batchId: string, nextStage: BatchStage): Promise<BatchSummary> => {
    try {
      const res = await api.post<BatchSummary>(`/batches/${batchId}/advance-stage`, { stage: nextStage });
      return res.data;
    } catch {
      const found = mockBatches.find(b => b.batch_id === batchId);
      if (found) {
        found.current_stage = nextStage;
        if (nextStage === 'HATCHED' || nextStage === 'COMPLETED') {
          found.status = 'COMPLETED';
          found.hatched_count = Math.round(found.initial_egg_count * 0.88);
          found.unhatched_count = found.initial_egg_count - found.hatched_count;
        }
        return found;
      }
      throw new Error("Batch not found");
    }
  },

  // Sessions
  getSessions: async (batchId?: string): Promise<CandlingSession[]> => {
    try {
      const res = await api.get<CandlingSession[]>('/sessions', { params: { batch_id: batchId } });
      return res.data;
    } catch {
      if (batchId) {
        return mockSessions.filter(s => s.batch_id === batchId);
      }
      return mockSessions;
    }
  },

  // Scans
  getScans: async (params?: { batch_id?: string; final_class?: string; limit?: number }): Promise<EggScan[]> => {
    try {
      const res = await api.get<EggScan[]>('/scans', { params });
      return res.data;
    } catch {
      let filtered = [...mockScans];
      if (params?.batch_id) {
        filtered = filtered.filter(s => s.batch_id === params.batch_id);
      }
      if (params?.final_class) {
        filtered = filtered.filter(s => s.final_class === params.final_class);
      }
      return filtered.slice(0, params?.limit || 50);
    }
  },

  // Devices
  getDevices: async (): Promise<Device[]> => {
    try {
      const res = await api.get<Device[]>('/devices');
      return res.data;
    } catch {
      return mockDevices;
    }
  },

  updateDeviceCalibration: async (deviceId: string, data: Partial<Device>): Promise<Device> => {
    try {
      const res = await api.patch<Device>(`/devices/${deviceId}`, data);
      return res.data;
    } catch {
      const found = mockDevices.find(d => d.device_id === deviceId);
      if (found) {
        Object.assign(found, data);
        return found;
      }
      throw new Error("Device not found");
    }
  },

  // Reports
  downloadCSVUrl: (batchId: string) => `/api/v1/reports/batch/${batchId}/csv`,
  downloadPDFUrl: (batchId: string) => `/api/v1/reports/batch/${batchId}/pdf`,
};
