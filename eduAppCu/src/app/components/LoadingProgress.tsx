import { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { Progress } from './ui/progress';

type LoadingProgressProps = {
  title: string;
  description?: string;
  stages?: string[];
};

export function LoadingProgress({ title, description, stages }: LoadingProgressProps) {
  const [progress, setProgress] = useState(8);
  const [stageIndex, setStageIndex] = useState(0);

  useEffect(() => {
    const interval = window.setInterval(() => {
      setProgress((value) => {
        if (value >= 92) return value;
        const step = value < 40 ? 6 : value < 70 ? 4 : 2;
        return Math.min(92, value + step);
      });
    }, 450);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!stages?.length) return;
    const interval = window.setInterval(() => {
      setStageIndex((index) => Math.min(index + 1, stages.length - 1));
    }, 2200);
    return () => window.clearInterval(interval);
  }, [stages]);

  const stageText = stages?.[stageIndex];

  return (
    <div className="bg-white rounded-2xl p-8 shadow-sm border border-border text-center max-w-sm w-full">
      <Loader2 className="size-12 animate-spin text-[#6D3DF5] mx-auto mb-4" />
      <h3 className="font-semibold text-lg mb-2">{title}</h3>
      {description && <p className="text-sm text-muted-foreground mb-4">{description}</p>}
      <Progress value={progress} className="h-2 mb-2" />
      <p className="text-xs text-muted-foreground">
        {stageText ?? `${Math.round(progress)}%`}
      </p>
    </div>
  );
}
