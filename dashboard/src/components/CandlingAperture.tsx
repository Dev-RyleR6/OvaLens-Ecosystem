import React, { useEffect, useState } from 'react';
import { ImageOff } from 'lucide-react';
import { FertilityClass } from '../types';

interface CandlingApertureProps {
  finalClass?: FertilityClass;
  confidence?: number;
  inferenceMs?: number;
  aspectRatio?: number;
  sequenceNumber?: number;
  batchId?: string;
  imageUrl?: string;
}

export const CandlingAperture: React.FC<CandlingApertureProps> = ({
  finalClass, confidence, inferenceMs, imageUrl,
}) => {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [imageUrl]);
  return (
    <figure className="space-y-3">
      <div className="h-56 bg-slate-50 border border-slate-200 rounded-lg overflow-hidden flex items-center justify-center">
        {imageUrl && !failed ? <img src={imageUrl} alt="Captured candling image for this egg scan" className="w-full h-full object-contain" loading="lazy" onError={() => setFailed(true)} /> : <div className="text-center text-slate-600 px-4"><ImageOff className="w-6 h-6 mx-auto mb-2" aria-hidden="true" /><p>{failed ? 'Scan image could not be loaded.' : 'No image uploaded for this scan.'}</p></div>}
      </div>
      <figcaption className="flex flex-wrap gap-x-5 gap-y-1 text-sm text-slate-600">
        <span>{finalClass === 'FERTILE' ? 'Fertile' : finalClass === 'INFERTILE' ? 'Infertile' : 'Classification unavailable'}</span>
        <span>Confidence: {confidence == null ? '—' : `${(confidence * 100).toFixed(1)}%`}</span>
        <span>Inference: {inferenceMs == null ? '—' : `${inferenceMs.toFixed(1)} ms`}</span>
      </figcaption>
    </figure>
  );
};
