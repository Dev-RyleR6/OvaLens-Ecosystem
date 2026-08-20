import React, { useState, useEffect } from 'react';
import { HeroCandlingVisualizer } from '../components/bento/HeroCandlingVisualizer';
import { HatcheryMetricsCard } from '../components/bento/HatcheryMetricsCard';
import { RadialBreedChart } from '../components/bento/RadialBreedChart';
import { IncubationTrackingCard } from '../components/bento/IncubationTrackingCard';
import { ScanLedgerCard } from '../components/bento/ScanLedgerCard';
import { HatcheryCopilot } from '../components/bento/HatcheryCopilot';
import { TrayMatrix } from '../components/TrayMatrix';
import { Sheet } from '../components/ui/sheet';
import { CandlingAperture } from '../components/CandlingAperture';
import { apiClient } from '../api/client';
import { AnalyticsOverview, BatchSummary, EggScan, EconomicYield } from '../types';
import { Layers, Sparkles } from 'lucide-react';

export const OverviewPage: React.FC = () => {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [economic, setEconomic] = useState<EconomicYield | null>(null);
  const [batches, setBatches] = useState<BatchSummary[]>([]);
  const [scans, setScans] = useState<EggScan[]>([]);
  const [selectedScan, setSelectedScan] = useState<EggScan | null>(null);
  const [showTrayModal, setShowTrayModal] = useState(false);

  useEffect(() => {
    const fetchDashboardData = async () => {
      const [overviewData, economicData, batchesData, scansData] = await Promise.all([
        apiClient.getOverview(),
        apiClient.getEconomicYield(),
        apiClient.getBatches(),
        apiClient.getScans({ limit: 20 })
      ]);
      setOverview(overviewData);
      setEconomic(economicData);
      setBatches(batchesData);
      setScans(scansData);
    };
    fetchDashboardData();
  }, []);

  return (
    <div className="space-y-5 pb-6">
      {/* Optional Top Quick Tray Access Strip */}
      <div className="flex items-center justify-between px-1">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-300">Active Incubation Matrix:</span>
          <button
            onClick={() => setShowTrayModal(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-[#161B27] hover:bg-[#1E2536] text-emerald-400 border border-emerald-500/30 transition-all cursor-pointer shadow-xs"
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Open 42-Egg Tray Heatmap</span>
          </button>
        </div>

        <div className="text-xs text-slate-400 font-medium hidden sm:block">
          Batch: <strong className="text-slate-200">BATCH-2026-08-KAY-01</strong> (Day 10)
        </div>
      </div>

      {/* 3-Column Bento Grid Layout (Exact Replica of Reference Dashboard) */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
        {/* ROW 1 */}
        {/* Card 1 (Top-Left): Hero Financial Value + 3D Candling Vision Box */}
        <HeroCandlingVisualizer
          totalRevenue={economic?.total_economic_benefit_php || 18540}
          growthPct={12.4}
          batchCode={batches[0]?.batch_code || "BATCH-2026-08-KAY-01"}
          activeEmbryoCount={overview?.total_fertile || 1812}
        />

        {/* Card 2 (Top-Middle): Hatchery & Incubation Metrics */}
        <HatcheryMetricsCard
          totalFertile={overview?.total_fertile || 1812}
          penoyRevenue={economic?.salvage_revenue_php || 2352}
          energySavedKwh={economic?.incubator_energy_saved_kwh || 45.4}
          cullRatePct={18}
        />

        {/* Card 3 (Top-Right): Smart Breed & Viability Breakdown */}
        <RadialBreedChart
          kayumanggiPct={91.2}
          itimPct={87.5}
          khakiPct={84.8}
          projectedGrowthPhp={12500}
        />

        {/* ROW 2 */}
        {/* Card 4 (Bottom-Left): Incubation Stage & Mortality Tracking */}
        <IncubationTrackingCard
          viableCount={451}
          totalSet={500}
          currentDay={10}
          fertilePct={90.2}
          penoyPct={7.4}
          abnormalPct={2.4}
          powerSpentPhp={1390}
          powerBudgetPhp={1600}
        />

        {/* Card 5 (Bottom-Middle): Live Candling Scan Ledger */}
        <ScanLedgerCard
          scans={scans}
          onSelectScan={(s) => setSelectedScan(s)}
        />

        {/* Card 6 (Bottom-Right): Hatchery AI Copilot & Triage Chat */}
        <HatcheryCopilot />
      </div>

      {/* Drawer for Inspecting Selected Scan from Ledger */}
      <Sheet
        isOpen={Boolean(selectedScan)}
        onClose={() => setSelectedScan(null)}
        title={selectedScan ? `Scan Details — #${selectedScan.sequence_number}` : ''}
        description={selectedScan ? `Batch: ${selectedScan.batch_id}` : ''}
      >
        {selectedScan && (
          <div className="space-y-4">
            <CandlingAperture
              finalClass={selectedScan.final_class}
              confidence={selectedScan.confidence}
              inferenceMs={selectedScan.inference_ms}
              sequenceNumber={selectedScan.sequence_number}
              batchId={selectedScan.batch_id}
              aspectRatio={0.78}
            />

            <div className="p-3.5 bg-[#161B27] rounded-xl border border-[#222A3B] space-y-1.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-200">Sorting Decision:</span>
                <span className={`font-bold ${selectedScan.routing_action === 'ACCEPT' ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {selectedScan.routing_action}
                </span>
              </div>
              <p className="text-slate-400 text-[11px]">
                {selectedScan.final_class === 'FERTILE'
                  ? 'Viable spider embryo veins confirmed by YOLOv8 vision engine.'
                  : 'Unfertilized yolk detected. Diverted to Penoy food market cull.'}
              </p>
            </div>
          </div>
        )}
      </Sheet>

      {/* Slide-over Sheet for 42-Egg Tray Heatmap */}
      <Sheet
        isOpen={showTrayModal}
        onClose={() => setShowTrayModal(false)}
        title="Incubator Tray Heatmap Matrix"
        description="Slot-by-slot duck egg candling classification for Batch BATCH-2026-08-KAY-01"
      >
        <div className="py-2">
          <TrayMatrix
            batchCode="BATCH-2026-08-KAY-01"
            trayNumber={1}
          />
        </div>
      </Sheet>
    </div>
  );
};
