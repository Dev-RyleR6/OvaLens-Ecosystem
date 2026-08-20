import React, { useState, useEffect } from 'react';
import {
  Plus,
  Search,
  Download,
  FileText,
  Layers,
  ChevronRight,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { BatchSummary, DuckBreed } from '../types';
import { Badge } from '../components/Badge';
import { BatchProgressTimeline } from '../components/BatchProgressTimeline';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select } from '../components/ui/select';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '../components/ui/table';
import { Dialog } from '../components/ui/dialog';
import { Sheet } from '../components/ui/sheet';

export const BatchesPage: React.FC = () => {
  const [batches, setBatches] = useState<BatchSummary[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [breedFilter, setBreedFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedBatch, setSelectedBatch] = useState<BatchSummary | null>(null);

  // New Batch Form State
  const [batchCode, setBatchCode] = useState('');
  const [breed, setBreed] = useState<DuckBreed>('KAYUMANGGI');
  const [incubatorId, setIncubatorId] = useState('INCUBATOR-A1');
  const [initialCount, setInitialCount] = useState(500);
  const [notes, setNotes] = useState('');

  const fetchBatches = async () => {
    const data = await apiClient.getBatches();
    setBatches(data);
  };

  useEffect(() => {
    fetchBatches();
  }, []);

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await apiClient.createBatch({
      batch_code: batchCode,
      breed,
      incubator_id: incubatorId,
      initial_egg_count: Number(initialCount),
      notes,
    });
    setIsCreateOpen(false);
    setBatchCode('');
    setNotes('');
    fetchBatches();
  };

  const filteredBatches = batches.filter((b) => {
    const matchSearch = b.batch_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
                        b.incubator_id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchBreed = breedFilter === 'ALL' || b.breed === breedFilter;
    const matchStatus = statusFilter === 'ALL' || b.status === statusFilter;
    return matchSearch && matchBreed && matchStatus;
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground">
            Incubation Batches
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Manage 28-day duck egg incubation cohorts, track milestones, and export reports.
          </p>
        </div>

        <Button
          variant="maroon"
          size="sm"
          onClick={() => setIsCreateOpen(true)}
          className="gap-1.5"
        >
          <Plus className="w-4 h-4" />
          Set New Batch
        </Button>
      </div>

      {/* Filter / Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 text-muted-foreground absolute left-2.5 top-1/2 -translate-y-1/2" />
          <Input
            type="text"
            placeholder="Search batch code or incubator..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Select
            value={breedFilter}
            onChange={(e) => setBreedFilter(e.target.value)}
            className="w-36 text-xs"
          >
            <option value="ALL">All Breeds</option>
            <option value="KAYUMANGGI">Kayumanggi</option>
            <option value="ITIM">Itim (Native)</option>
            <option value="KHAKI">Khaki Campbell</option>
          </Select>

          <Select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-36 text-xs"
          >
            <option value="ALL">All Statuses</option>
            <option value="INCUBATING">Incubating</option>
            <option value="COMPLETED">Completed</option>
          </Select>
        </div>
      </div>

      {/* Batches Table Card */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Batch Code</TableHead>
              <TableHead>Duck Breed</TableHead>
              <TableHead>Incubator</TableHead>
              <TableHead>Initial Set</TableHead>
              <TableHead>Current Stage</TableHead>
              <TableHead>Fertility Rate</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredBatches.map((b) => (
              <TableRow
                key={b.batch_id}
                className="cursor-pointer"
                onClick={() => setSelectedBatch(b)}
              >
                <TableCell className="font-medium text-foreground">
                  <div className="flex items-center gap-2">
                    <Layers className="w-3.5 h-3.5 text-muted-foreground" />
                    <span>{b.batch_code}</span>
                  </div>
                  <span className="text-[11px] text-muted-foreground block">
                    Set: {new Date(b.set_date).toLocaleDateString()}
                  </span>
                </TableCell>
                <TableCell>{b.breed}</TableCell>
                <TableCell className="text-muted-foreground">{b.incubator_id}</TableCell>
                <TableCell>{b.initial_egg_count} eggs</TableCell>
                <TableCell>
                  <Badge type="stage" value={b.current_stage} />
                </TableCell>
                <TableCell className="font-semibold">
                  {b.fertility_rate > 0 ? `${b.fertility_rate}%` : 'Pending'}
                </TableCell>
                <TableCell>
                  <Badge type="status" value={b.status} />
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-1" onClick={(e) => e.stopPropagation()}>
                    <a
                      href={apiClient.downloadCSVUrl(b.batch_id)}
                      download
                      className="p-1.5 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors inline-block"
                      title="Export CSV"
                    >
                      <Download className="w-3.5 h-3.5" />
                    </a>
                    <a
                      href={apiClient.downloadPDFUrl(b.batch_id)}
                      target="_blank"
                      rel="noreferrer"
                      className="p-1.5 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors inline-block"
                      title="Download PDF Certificate"
                    >
                      <FileText className="w-3.5 h-3.5" />
                    </a>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-muted-foreground"
                      onClick={() => setSelectedBatch(b)}
                    >
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      {/* New Batch Dialog */}
      <Dialog
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Set New Incubation Batch"
        description="Configure a new 28-day duck egg incubation cohort."
      >
        <form onSubmit={handleCreateSubmit} className="space-y-4 text-sm">
          <div className="space-y-1.5">
            <label className="font-medium text-xs text-foreground">Batch Identifier</label>
            <Input
              required
              placeholder="e.g. BATCH-2026-08-KAY-03"
              value={batchCode}
              onChange={(e) => setBatchCode(e.target.value)}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="font-medium text-xs text-foreground">Duck Breed</label>
              <Select
                value={breed}
                onChange={(e) => setBreed(e.target.value as DuckBreed)}
              >
                <option value="KAYUMANGGI">Kayumanggi</option>
                <option value="ITIM">Itim (Native)</option>
                <option value="KHAKI">Khaki Campbell</option>
              </Select>
            </div>
            <div className="space-y-1.5">
              <label className="font-medium text-xs text-foreground">Incubator Unit</label>
              <Input
                required
                value={incubatorId}
                onChange={(e) => setIncubatorId(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="font-medium text-xs text-foreground">Initial Egg Count</label>
            <Input
              type="number"
              min="1"
              required
              value={initialCount}
              onChange={(e) => setInitialCount(Number(e.target.value))}
            />
          </div>

          <div className="space-y-1.5">
            <label className="font-medium text-xs text-foreground">Flock & Source Notes</label>
            <textarea
              rows={3}
              placeholder="Breeder origin, initial candling notes, incubator set condition..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-xs placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </div>

          <div className="pt-3 flex items-center justify-end gap-2 border-t">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsCreateOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" variant="maroon" size="sm">
              Initialize Batch
            </Button>
          </div>
        </form>
      </Dialog>

      {/* Batch Details Drawer (Sheet) */}
      <Sheet
        isOpen={Boolean(selectedBatch)}
        onClose={() => setSelectedBatch(null)}
        title={selectedBatch ? `Batch: ${selectedBatch.batch_code}` : ''}
        description="Detailed incubation lifecycle and candling yield statistics"
      >
        {selectedBatch && (
          <div className="space-y-5 text-sm">
            {/* Timeline */}
            <div className="p-4 bg-muted/40 rounded-lg border">
              <h4 className="text-xs font-semibold text-foreground mb-1">Incubation Progress</h4>
              <BatchProgressTimeline
                currentStage={selectedBatch.current_stage}
                setDate={selectedBatch.set_date}
              />
            </div>

            {/* Core Stats */}
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="p-3 bg-muted/30 rounded border">
                <span className="text-muted-foreground text-[11px] block">Duck Breed</span>
                <span className="font-semibold text-foreground text-sm mt-0.5 block">{selectedBatch.breed}</span>
              </div>
              <div className="p-3 bg-muted/30 rounded border">
                <span className="text-muted-foreground text-[11px] block">Incubator Unit</span>
                <span className="font-semibold text-foreground text-sm mt-0.5 block">{selectedBatch.incubator_id}</span>
              </div>
              <div className="p-3 bg-muted/30 rounded border">
                <span className="text-muted-foreground text-[11px] block">Initial Set Count</span>
                <span className="font-semibold text-foreground text-sm mt-0.5 block">{selectedBatch.initial_egg_count} eggs</span>
              </div>
              <div className="p-3 bg-muted/30 rounded border">
                <span className="text-muted-foreground text-[11px] block">Fertility Rate</span>
                <span className="font-semibold text-emerald-600 dark:text-emerald-400 text-sm mt-0.5 block">{selectedBatch.fertility_rate}%</span>
              </div>
            </div>

            {/* Classification Breakdown */}
            <div className="p-3 bg-muted/30 rounded border space-y-2">
              <h4 className="text-xs font-semibold text-foreground">Candling Yield Breakdown</h4>
              <div className="grid grid-cols-3 gap-2 text-center text-xs">
                <div className="p-2 bg-emerald-50 dark:bg-emerald-950/30 rounded border border-emerald-200 dark:border-emerald-900">
                  <span className="text-[10px] text-emerald-700 dark:text-emerald-400 font-medium block">Fertile</span>
                  <span className="text-base font-bold text-foreground">{selectedBatch.fertile_count}</span>
                </div>
                <div className="p-2 bg-amber-50 dark:bg-amber-950/30 rounded border border-amber-200 dark:border-amber-900">
                  <span className="text-[10px] text-amber-800 dark:text-amber-300 font-medium block">Penoy</span>
                  <span className="text-base font-bold text-foreground">{selectedBatch.infertile_count}</span>
                </div>
                <div className="p-2 bg-rose-50 dark:bg-rose-950/30 rounded border border-rose-200 dark:border-rose-900">
                  <span className="text-[10px] text-rose-700 dark:text-rose-400 font-medium block">Abnormal</span>
                  <span className="text-base font-bold text-foreground">{selectedBatch.abnormal_count}</span>
                </div>
              </div>
            </div>

            {/* Notes if any */}
            {selectedBatch.notes && (
              <div className="p-3 bg-muted/30 rounded border text-xs">
                <span className="font-medium text-foreground block mb-1">Notes:</span>
                <p className="text-muted-foreground">{selectedBatch.notes}</p>
              </div>
            )}

            {/* Export Actions */}
            <div className="pt-2 flex items-center justify-end gap-2 border-t">
              <a
                href={apiClient.downloadCSVUrl(selectedBatch.batch_id)}
                download
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border hover:bg-muted transition-colors"
              >
                <Download className="w-3.5 h-3.5" /> CSV Data
              </a>
              <a
                href={apiClient.downloadPDFUrl(selectedBatch.batch_id)}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-[#800000] text-white hover:bg-[#6e0000] transition-colors"
              >
                <FileText className="w-3.5 h-3.5" /> PDF Certificate
              </a>
            </div>
          </div>
        )}
      </Sheet>
    </div>
  );
};
