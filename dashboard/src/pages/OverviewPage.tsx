import React, { useState, useEffect } from 'react';
import {
  Activity,
  Layers,
  Coins,
  CheckCircle2,
  Calendar,
  ArrowRight,
  TrendingUp,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
} from 'recharts';

import { StatCard } from '../components/StatCard';
import { Badge } from '../components/Badge';
import { TrayMatrix } from '../components/TrayMatrix';
import { BatchProgressTimeline } from '../components/BatchProgressTimeline';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '../components/ui/table';
import { Button } from '../components/ui/button';
import { apiClient } from '../api/client';
import { AnalyticsOverview, BatchSummary, EggScan } from '../types';

export const OverviewPage: React.FC = () => {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [batches, setBatches] = useState<BatchSummary[]>([]);
  const [recentScans, setRecentScans] = useState<EggScan[]>([]);
  const [selectedBatch, setSelectedBatch] = useState<BatchSummary | null>(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      const [overviewData, batchesData, scansData] = await Promise.all([
        apiClient.getOverview(),
        apiClient.getBatches(),
        apiClient.getScans({ limit: 8 })
      ]);
      setOverview(overviewData);
      setBatches(batchesData);
      setRecentScans(scansData);
      if (batchesData.length > 0) {
        setSelectedBatch(batchesData[0]);
      }
    };
    fetchDashboardData();
  }, []);

  const fertilityData = [
    { name: 'Fertile (Accept)', count: overview?.total_fertile || 1812, color: '#16A34A' },
    { name: 'Infertile (Penoy)', count: overview?.total_infertile || 168, color: '#D97706' },
    { name: 'Abnormal (Dead)', count: overview?.total_abnormal || 70, color: '#DC2626' },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground">
            Hatchery Overview
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Duck egg candling classification, incubation milestones, and salvage analytics.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link to="/batches">
            <Button variant="outline" size="sm" className="text-xs">
              View All Batches
            </Button>
          </Link>
        </div>
      </div>

      {/* 4 Clean Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Eggs Candled"
          value={overview ? overview.total_eggs_scanned.toLocaleString() : '2,050'}
          unit="eggs"
          subtitle="Computer vision verified"
          icon={Activity}
        />
        <StatCard
          title="Overall Fertility Rate"
          value={overview ? `${overview.overall_fertility_rate}%` : '88.4%'}
          subtitle={`${overview?.total_fertile || 1812} viable embryos`}
          icon={CheckCircle2}
          trend={{ value: '+2.1%', isPositive: true, label: 'vs last batch' }}
        />
        <StatCard
          title="Day 10 Penoy Salvage"
          value={`₱${((overview?.total_infertile || 168) * 14.0).toLocaleString('en-US', { minimumFractionDigits: 2 })}`}
          subtitle={`${overview?.total_infertile || 168} eggs @ ₱14.00/egg`}
          icon={Coins}
        />
        <StatCard
          title="Active Incubating Batches"
          value={overview ? overview.active_batches_count : '3'}
          unit="batches"
          subtitle="In incubation cycle"
          icon={Layers}
        />
      </div>

      {/* Main Content Grid: Tray Matrix + Fertility Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left 7 Cols: Clean 42-Egg Tray Matrix */}
        <div className="lg:col-span-7">
          <TrayMatrix
            batchCode={selectedBatch?.batch_code || "BATCH-2026-08-KAY-01"}
            trayNumber={1}
          />
        </div>

        {/* Right 5 Cols: Fertility Distribution Card */}
        <div className="lg:col-span-5">
          <Card className="h-full flex flex-col justify-between">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold">Fertility Classification</CardTitle>
              <CardDescription className="text-xs">3-class YOLOv8 vision classification breakdown</CardDescription>
            </CardHeader>

            <CardContent className="space-y-4 my-auto">
              <div className="h-44 relative flex items-center justify-center">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={fertilityData}
                      cx="50%"
                      cy="50%"
                      innerRadius={48}
                      outerRadius={68}
                      paddingAngle={3}
                      dataKey="count"
                    >
                      {fertilityData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'var(--card)',
                        borderColor: 'var(--border)',
                        borderRadius: '0.5rem',
                        fontSize: '12px',
                        color: 'var(--foreground)'
                      }}
                      formatter={(val: any, name: any) => [`${val} eggs`, name]}
                    />
                  </PieChart>
                </ResponsiveContainer>

                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                  <span className="text-xl font-bold tracking-tight text-foreground">
                    {overview ? `${overview.overall_fertility_rate}%` : '88.4%'}
                  </span>
                  <span className="text-[10px] text-muted-foreground font-medium">Fertility</span>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2 text-center text-xs pt-1">
                <div className="p-2 rounded-md bg-emerald-50/60 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-900">
                  <span className="text-emerald-700 dark:text-emerald-400 font-semibold block">{overview?.total_fertile || 1812}</span>
                  <span className="text-[10px] text-muted-foreground">Fertile</span>
                </div>
                <div className="p-2 rounded-md bg-amber-50/60 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900">
                  <span className="text-amber-800 dark:text-amber-300 font-semibold block">{overview?.total_infertile || 168}</span>
                  <span className="text-[10px] text-muted-foreground">Penoy</span>
                </div>
                <div className="p-2 rounded-md bg-rose-50/60 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900">
                  <span className="text-rose-700 dark:text-rose-400 font-semibold block">{overview?.total_abnormal || 70}</span>
                  <span className="text-[10px] text-muted-foreground">Abnormal</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Active Incubation Lifecycle Card */}
      {selectedBatch && (
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base font-semibold">
                  Active Batch: {selectedBatch.batch_code}
                </CardTitle>
                <CardDescription className="text-xs">
                  Breed: {selectedBatch.breed} • Incubator: {selectedBatch.incubator_id} • {selectedBatch.initial_egg_count} eggs set
                </CardDescription>
              </div>
              <Badge type="status" value={selectedBatch.status} />
            </div>
          </CardHeader>
          <CardContent>
            <BatchProgressTimeline
              currentStage={selectedBatch.current_stage}
              setDate={selectedBatch.set_date}
            />
          </CardContent>
        </Card>
      )}

      {/* Recent Scans Activity Table */}
      <Card>
        <CardHeader className="pb-3 flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-base font-semibold">Recent Candling Scans</CardTitle>
            <CardDescription className="text-xs">Latest automated candling classifications</CardDescription>
          </div>
          <Link to="/scans">
            <Button variant="ghost" size="sm" className="text-xs text-muted-foreground gap-1">
              View all <ArrowRight className="w-3.5 h-3.5" />
            </Button>
          </Link>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-16">#</TableHead>
                <TableHead>Batch</TableHead>
                <TableHead>Classification</TableHead>
                <TableHead>Confidence</TableHead>
                <TableHead>Action</TableHead>
                <TableHead className="text-right">Timestamp</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recentScans.map((scan) => (
                <TableRow key={scan.scan_id}>
                  <TableCell className="font-medium text-muted-foreground">
                    #{scan.sequence_number}
                  </TableCell>
                  <TableCell className="text-foreground">{scan.batch_id}</TableCell>
                  <TableCell>
                    <Badge type="fertility" value={scan.final_class} />
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {(scan.confidence * 100).toFixed(1)}%
                  </TableCell>
                  <TableCell>
                    <span
                      className={`text-xs font-medium ${
                        scan.routing_action === 'ACCEPT' ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'
                      }`}
                    >
                      {scan.routing_action}
                    </span>
                  </TableCell>
                  <TableCell className="text-right text-xs text-muted-foreground">
                    {new Date(scan.scanned_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
};
