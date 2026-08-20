import React, { useState, useEffect } from 'react';
import {
  Coins,
  TrendingUp,
  Zap,
  Award,
  Calculator,
  ShieldAlert,
  Percent,
  CheckCircle2,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
} from 'recharts';

import { StatCard } from '../components/StatCard';
import { apiClient } from '../api/client';
import { EconomicYield, MortalityTrends, BreedMetricItem } from '../types';

export const AnalyticsPage: React.FC = () => {
  const [economic, setEconomic] = useState<EconomicYield | null>(null);
  const [mortality, setMortality] = useState<MortalityTrends | null>(null);
  const [breedMetrics, setBreedMetrics] = useState<BreedMetricItem[]>([]);

  // Dynamic Financial Simulator sliders
  const [customEggs, setCustomEggs] = useState(168);
  const [customPrice, setCustomPrice] = useState(14.00);
  const [ducklingPrice, setDucklingPrice] = useState(40.00);
  const [electricityRate, setElectricityRate] = useState(12.50); // PHP per kWh

  useEffect(() => {
    const fetchData = async () => {
      const [eData, mData, bData] = await Promise.all([
        apiClient.getEconomicYield(),
        apiClient.getMortalityTrends(),
        apiClient.getBreedComparison(),
      ]);
      setEconomic(eData);
      setMortality(mData);
      setBreedMetrics(bData);
    };
    fetchData();
  }, []);

  // 28-day duck egg developmental viability curve
  const cohortSurvivalData = [
    { day: 'Day 0 (Set)', viablePct: 100 },
    { day: 'Day 10 (1st Candle)', viablePct: 91.2 },
    { day: 'Day 18 (Transfer)', viablePct: 88.5 },
    { day: 'Day 25 (Pipping)', viablePct: 87.1 },
    { day: 'Day 28 (Hatch)', viablePct: 86.8 },
  ];

  // Mortality Stages Data
  const mortalityBarData = [
    {
      stage: 'Day 10 (Early / Penoy)',
      rate: mortality?.day_10_early_mortality_rate || 8.8,
      desc: 'Unfertilized yolk / dead germinal disc (100% salvaged @ ₱14)',
      color: '#D97706',
    },
    {
      stage: 'Day 18 (Mid-Term)',
      rate: mortality?.day_18_mid_mortality_rate || 3.2,
      desc: 'Mid embryonic arrest before hatcher transfer',
      color: '#DC2626',
    },
    {
      stage: 'Day 25 (Late / Pipping)',
      rate: mortality?.day_25_late_mortality_rate || 1.4,
      desc: 'Late dead-in-shell during shell pipping',
      color: '#991B1B',
    },
  ];

  // Dynamic calculations
  const dynamicPenoySales = customEggs * customPrice;
  const dynamicKwhSaved = customEggs * 18 * 0.015; // 0.015 kWh/egg/day across 18 days
  const dynamicPowerSavings = dynamicKwhSaved * electricityRate;
  const projectedDucklings = 450 * 0.88; // 88% hatchability
  const dynamicDucklingRevenue = projectedDucklings * ducklingPrice;
  const dynamicTotalBenefit = dynamicPenoySales + dynamicPowerSavings;

  return (
    <div className="space-y-6 pb-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-[#0F172A] tracking-tight">
            Hatchery Economics & Salvage Analytics
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Commercial recovery from Day 10 Penoy culling, incubator thermal energy savings, and duck breed yield benchmarks.
          </p>
        </div>

        <span className="text-xs font-semibold text-[#800000] bg-maroon-50 border border-maroon-200 px-3 py-1 rounded-full">
          Foundation University Research Division
        </span>
      </div>

      {/* 4 Clean Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Penoy Eggs Salvaged"
          value={economic ? `${economic.penoy_culled_day_10}` : '168'}
          unit="eggs"
          subtitle="Culled on Day 10 candling"
          icon={Coins}
          highlightColor="amber"
        />
        <StatCard
          title="Penoy Salvage Revenue"
          value={economic ? `₱${economic.salvage_revenue_php.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '₱2,352.00'}
          subtitle={`@ ₱${economic ? economic.penoy_unit_price_php : 14.0}/egg market rate`}
          icon={TrendingUp}
          highlightColor="amber"
        />
        <StatCard
          title="Incubator Energy Saved"
          value={economic ? `${economic.incubator_energy_saved_kwh.toFixed(1)}` : '45.4'}
          unit="kWh"
          subtitle={`₱${economic ? economic.energy_savings_php.toFixed(2) : '544.32'} thermal power avoided`}
          icon={Zap}
          highlightColor="blue"
        />
        <StatCard
          title="Total Economic Benefit"
          value={economic ? `₱${economic.total_economic_benefit_php.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '₱24,176.32'}
          subtitle="Direct sales + avoided power"
          icon={Award}
          highlightColor="green"
        />
      </div>

      {/* Interactive Day-10 Penoy Economic Calculator Card */}
      <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-xs">
        <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
          <Calculator className="w-4 h-4 text-[#800000]" />
          <div>
            <h3 className="text-base font-bold text-[#0F172A]">
              Day-10 Penoy Economic Yield Simulator
            </h3>
            <p className="text-xs text-slate-500">
              Estimate commercial revenue recovered by early culling unfertilized eggs on Day 10 instead of waiting until Day 28.
            </p>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Slider 1: Eggs Culled */}
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
            <div className="flex justify-between text-xs">
              <label className="font-bold text-slate-700">Day 10 Infertile Eggs:</label>
              <span className="font-extrabold text-[#800000]">{customEggs} eggs</span>
            </div>
            <input
              type="range"
              min="0"
              max="500"
              step="5"
              value={customEggs}
              onChange={(e) => setCustomEggs(Number(e.target.value))}
              className="w-full accent-[#800000] cursor-pointer"
            />
            <span className="text-[11px] text-slate-500 block">Simulate 0 to 500 tray capacity</span>
          </div>

          {/* Slider 2: Penoy Market Price */}
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
            <div className="flex justify-between text-xs">
              <label className="font-bold text-slate-700">Penoy Selling Price:</label>
              <span className="font-extrabold text-amber-700">₱{customPrice.toFixed(2)} / egg</span>
            </div>
            <input
              type="range"
              min="10"
              max="22"
              step="0.5"
              value={customPrice}
              onChange={(e) => setCustomPrice(Number(e.target.value))}
              className="w-full accent-[#800000] cursor-pointer"
            />
            <span className="text-[11px] text-slate-500 block">Local commercial market: ₱12–₱18 / egg</span>
          </div>

          {/* Calculated Output Box */}
          <div className="p-4 bg-amber-50 rounded-xl border border-amber-200 flex flex-col justify-center text-center">
            <span className="text-xs text-amber-800 font-bold uppercase tracking-wider">
              Total Economic Value Recovered
            </span>
            <span className="text-2xl font-black text-amber-900 mt-1">
              ₱{dynamicTotalBenefit.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </span>
            <span className="text-[11px] text-amber-700 font-medium mt-0.5">
              ₱{dynamicPenoySales.toFixed(2)} food salvage + ₱{dynamicPowerSavings.toFixed(2)} power saved
            </span>
          </div>
        </div>
      </div>

      {/* Split: Embryonic Mortality Breakdown + Cohort Survival Curve */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left 6 Cols: 3-Stage Incubation Mortality Breakdown */}
        <div className="lg:col-span-6">
          <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-xs h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div>
                  <h3 className="text-sm font-bold text-[#0F172A]">
                    Embryonic Mortality by Stage
                  </h3>
                  <p className="text-xs text-slate-500">Early arrest vs Mid-term vs Late pipping failure</p>
                </div>
                <span className="text-xs font-semibold text-rose-700 bg-rose-50 px-2.5 py-0.5 rounded-full border border-rose-200">
                  {mortality?.total_culled_eggs || 238} Culled Eggs Total
                </span>
              </div>

              {/* Stage Breakdown Bars */}
              <div className="space-y-3.5 mt-4">
                {mortalityBarData.map((st) => (
                  <div key={st.stage} className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-slate-800">{st.stage}</span>
                      <span className="font-extrabold text-slate-900">{st.rate}% mortality</span>
                    </div>
                    <div className="h-2 w-full bg-slate-200 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${st.rate * 5}%`, backgroundColor: st.color }}
                      />
                    </div>
                    <p className="text-[11px] text-slate-500">{st.desc}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-100 text-xs text-slate-600 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-700 flex-shrink-0" />
              <span>Day 10 candling eliminates <strong>65% of all potential hatchery losses</strong> early.</span>
            </div>
          </div>
        </div>

        {/* Right 6 Cols: 28-Day Embryonic Viability Area Curve */}
        <div className="lg:col-span-6">
          <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-xs h-full flex flex-col justify-between">
            <div>
              <div className="pb-3 border-b border-slate-100">
                <h3 className="text-sm font-bold text-[#0F172A]">
                  28-Day Embryonic Viability Retention
                </h3>
                <p className="text-xs text-slate-500">Live embryo retention curve across incubation milestones</p>
              </div>

              <div className="h-60 mt-3">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={cohortSurvivalData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="viabilityGradientFU" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#15803D" stopOpacity={0.35}/>
                        <stop offset="95%" stopColor="#15803D" stopOpacity={0.0}/>
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="day" stroke="#64748B" fontSize={11} tickLine={false} />
                    <YAxis domain={[75, 100]} stroke="#64748B" fontSize={11} tickLine={false} unit="%" />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#FFFFFF',
                        borderColor: '#E2E8F0',
                        borderRadius: '0.5rem',
                        fontSize: '12px',
                        color: '#0F172A',
                      }}
                      formatter={(val: any) => [`${val}%`, 'Viable Embryos']}
                    />
                    <Area type="monotone" dataKey="viablePct" stroke="#15803D" strokeWidth={2.5} fillOpacity={1} fill="url(#viabilityGradientFU)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-100 text-xs text-slate-500 text-right">
              Overall Hatch Harvest Rate: <strong className="text-emerald-800">86.8%</strong>
            </div>
          </div>
        </div>
      </div>

      {/* Duck Breed Performance Comparison Matrix */}
      <div className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-xs">
        <div className="pb-3 border-b border-slate-100">
          <h3 className="text-base font-bold text-[#0F172A]">
            Duck Breed Biological & Commercial Benchmarks
          </h3>
          <p className="text-xs text-slate-500">
            Comparative performance across Kayumanggi, Native Itim, and Khaki Campbell flocks
          </p>
        </div>

        <div className="overflow-x-auto mt-3">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-3 px-4">Duck Breed</th>
                <th className="py-3 px-4">Total Evaluated</th>
                <th className="py-3 px-4">Fertile Count</th>
                <th className="py-3 px-4">Fertility Rate</th>
                <th className="py-3 px-4">Penoy Culled</th>
                <th className="py-3 px-4">Hatched Count</th>
                <th className="py-3 px-4 text-right">Hatchability</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {breedMetrics.map((b) => (
                <tr key={b.breed} className="hover:bg-slate-50 transition-colors">
                  <td className="py-3 px-4 font-bold text-[#0F172A]">{b.breed}</td>
                  <td className="py-3 px-4 text-slate-700 font-medium">{b.total_eggs} eggs</td>
                  <td className="py-3 px-4 text-emerald-700 font-bold">{b.fertile_count}</td>
                  <td className="py-3 px-4 font-bold text-emerald-800">{b.fertility_rate}%</td>
                  <td className="py-3 px-4 text-amber-800 font-semibold">{b.infertile_count} ({((b.infertile_count / b.total_eggs) * 100).toFixed(1)}%)</td>
                  <td className="py-3 px-4 text-slate-800 font-bold">{b.hatched_count}</td>
                  <td className="py-3 px-4 text-right font-extrabold text-slate-900">{b.hatchability_rate}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
