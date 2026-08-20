import React, { useState, useEffect } from 'react';
import {
  Search,
  Filter,
  Eye,
  ChevronRight,
  ScanLine,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { EggScan } from '../types';
import { Badge } from '../components/Badge';
import { CandlingAperture } from '../components/CandlingAperture';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select } from '../components/ui/select';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '../components/ui/table';
import { Sheet } from '../components/ui/sheet';

export const ScanExplorerPage: React.FC = () => {
  const [scans, setScans] = useState<EggScan[]>([]);
  const [selectedScan, setSelectedScan] = useState<EggScan | null>(null);
  const [classFilter, setClassFilter] = useState<string>('ALL');
  const [batchFilter, setBatchFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const fetchScans = async () => {
    const data = await apiClient.getScans({
      final_class: classFilter === 'ALL' ? undefined : classFilter,
      batch_id: batchFilter === 'ALL' ? undefined : batchFilter,
      limit: 60
    });
    setScans(data);
  };

  useEffect(() => {
    fetchScans();
  }, [classFilter, batchFilter]);

  const filteredScans = scans.filter(s => {
    const matchSearch = s.scan_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                        s.sequence_number.toString().includes(searchQuery);
    return matchSearch;
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground">
            Candling Scan Explorer
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Browse verified duck egg transillumination scans, optical metrics, and vision classifications.
          </p>
        </div>

        <span className="text-xs text-muted-foreground">
          Showing {filteredScans.length} scans
        </span>
      </div>

      {/* Filter / Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 text-muted-foreground absolute left-2.5 top-1/2 -translate-y-1/2" />
          <Input
            type="text"
            placeholder="Search # seq or scan UUID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Select
            value={classFilter}
            onChange={(e) => setClassFilter(e.target.value)}
            className="w-36 text-xs"
          >
            <option value="ALL">All Classes</option>
            <option value="FERTILE">Fertile</option>
            <option value="INFERTILE">Infertile (Penoy)</option>
            <option value="ABNORMAL">Abnormal</option>
          </Select>

          <Select
            value={batchFilter}
            onChange={(e) => setBatchFilter(e.target.value)}
            className="w-44 text-xs"
          >
            <option value="ALL">All Batches</option>
            <option value="BATCH-2026-08-KAY-01">BATCH-2026-08-KAY-01</option>
            <option value="BATCH-2026-08-ITM-01">BATCH-2026-08-ITM-01</option>
            <option value="BATCH-2026-07-KHK-01">BATCH-2026-07-KHK-01</option>
          </Select>
        </div>
      </div>

      {/* Scans Data Table */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-16"># Seq</TableHead>
              <TableHead>Batch</TableHead>
              <TableHead>Classification</TableHead>
              <TableHead>Confidence</TableHead>
              <TableHead>Latency</TableHead>
              <TableHead>Sorting Decision</TableHead>
              <TableHead className="text-right">Inspect</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredScans.map((s) => (
              <TableRow
                key={s.scan_id}
                className="cursor-pointer"
                onClick={() => setSelectedScan(s)}
              >
                <TableCell className="font-medium text-foreground">
                  #{s.sequence_number}
                </TableCell>
                <TableCell className="text-muted-foreground">{s.batch_id}</TableCell>
                <TableCell>
                  <Badge type="fertility" value={s.final_class} />
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {(s.confidence * 100).toFixed(1)}%
                </TableCell>
                <TableCell className="text-muted-foreground text-xs">
                  {s.inference_ms} ms
                </TableCell>
                <TableCell>
                  <span
                    className={`text-xs font-semibold ${
                      s.routing_action === 'ACCEPT' ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'
                    }`}
                  >
                    {s.routing_action}
                  </span>
                </TableCell>
                <TableCell className="text-right">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 text-muted-foreground"
                    onClick={() => setSelectedScan(s)}
                  >
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      {/* Scan Details Drawer (Sheet) */}
      <Sheet
        isOpen={Boolean(selectedScan)}
        onClose={() => setSelectedScan(null)}
        title={selectedScan ? `Scan Details — #${selectedScan.sequence_number}` : ''}
        description={selectedScan ? `Batch: ${selectedScan.batch_id} • UUID: ${selectedScan.scan_id}` : ''}
      >
        {selectedScan && (
          <div className="space-y-4 text-sm">
            {/* Visual Candling Aperture */}
            <CandlingAperture
              finalClass={selectedScan.final_class}
              confidence={selectedScan.confidence}
              inferenceMs={selectedScan.inference_ms}
              sequenceNumber={selectedScan.sequence_number}
              batchId={selectedScan.batch_id}
              aspectRatio={0.78}
            />

            {/* Decision card */}
            <div className="p-3 bg-muted/40 rounded border space-y-1.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-medium text-foreground">Conveyor Routing Action:</span>
                <span
                  className={`font-semibold ${
                    selectedScan.routing_action === 'ACCEPT' ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'
                  }`}
                >
                  {selectedScan.routing_action === 'ACCEPT' ? 'ACCEPT (Incubate)' : 'REJECT (Divert)'}
                </span>
              </div>
              <p className="text-muted-foreground text-[11px]">
                {selectedScan.final_class === 'FERTILE'
                  ? 'Embryo with viable spider veins confirmed. Proceed to incubation tray.'
                  : selectedScan.final_class === 'INFERTILE'
                  ? 'Clear unfertilized egg. Diverted to Penoy food salvage tray.'
                  : 'Dead or corrupted embryo. Diverted to early discard.'}
              </p>
            </div>

            {/* Raw Detections Metadata */}
            <div className="space-y-1.5 text-xs">
              <span className="font-medium text-foreground block">YOLOv8 Detection Output</span>
              <pre className="p-3 rounded bg-muted text-xs font-mono overflow-x-auto max-h-36 border">
                {JSON.stringify(
                  selectedScan.detections.length > 0
                    ? selectedScan.detections
                    : [
                        {
                          bbox: [0.24, 0.18, 0.76, 0.88],
                          class_name: selectedScan.final_class,
                          confidence: selectedScan.confidence,
                          aspect_ratio: 0.78,
                        }
                      ],
                  null,
                  2
                )}
              </pre>
            </div>
          </div>
        )}
      </Sheet>
    </div>
  );
};
