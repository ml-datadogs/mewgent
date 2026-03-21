import { StatRadar } from '@/components/StatRadar';
import { STAT_ORDER, STAT_LABELS, STAT_COLORS, type SaveCat, type StatKey } from '@/types';

interface AvgRadarProps {
  cats: SaveCat[];
}

export function AvgRadar({ cats }: AvgRadarProps) {
  if (cats.length === 0) {
    return <div className="text-center text-text-dim text-xs py-8">No cats</div>;
  }

  const n = cats.length;
  const avgVals: number[] = [];
  const minVals: number[] = [];
  const maxVals: number[] = [];

  for (const key of STAT_ORDER) {
    const vals = cats.map((c) => c[`base_${key}` as keyof SaveCat] as number);
    avgVals.push(vals.reduce((a, b) => a + b, 0) / n);
    minVals.push(Math.min(...vals));
    maxVals.push(Math.max(...vals));
  }

  return (
    <div className="flex flex-col items-center gap-2 py-2">
      <span className="text-[10px] font-mono text-text-dim font-bold">
        Average Stats ({n} cats)
      </span>

      <StatRadar
        values={avgVals}
        rangeMin={minVals}
        rangeMax={maxVals}
        size={180}
        showLabels
      />

      <div className="flex gap-1.5 flex-wrap justify-center">
        {STAT_ORDER.map((key, i) => {
          const color = avgVals[i] >= 5.5
            ? STAT_COLORS[key as StatKey]
            : 'var(--color-text-dim)';
          return (
            <span
              key={key}
              className="text-[9px] font-mono font-bold"
              style={{ color }}
            >
              {STAT_LABELS[i]} {avgVals[i].toFixed(1)}
            </span>
          );
        })}
      </div>
    </div>
  );
}
