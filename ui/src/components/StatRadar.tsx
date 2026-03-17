import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { STAT_ORDER, STAT_LABELS, STAT_COLORS, type SaveCat, type StatKey } from '@/types';

interface StatRadarProps {
  cat?: SaveCat;
  values?: number[];
  rangeMin?: number[];
  rangeMax?: number[];
  size?: number;
  showLabels?: boolean;
}

function catToRadarData(cat: SaveCat) {
  return STAT_ORDER.map((key, i) => ({
    stat: STAT_LABELS[i],
    value: cat[`base_${key}` as keyof SaveCat] as number,
    fullMark: 10,
    color: STAT_COLORS[key],
  }));
}

function valuesToRadarData(values: number[]) {
  return STAT_ORDER.map((key, i) => ({
    stat: STAT_LABELS[i],
    value: values[i] ?? 0,
    fullMark: 10,
    color: STAT_COLORS[key],
  }));
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CustomTick(props: any) {
  const { x, y, payload } = props;
  const idx = STAT_LABELS.indexOf(payload?.value as typeof STAT_LABELS[number]);
  const key = idx >= 0 ? STAT_ORDER[idx] : 'str';
  return (
    <text
      x={x}
      y={y}
      textAnchor="middle"
      dominantBaseline="central"
      fill={STAT_COLORS[key as StatKey]}
      fontSize={9}
      fontFamily="'JetBrains Mono', monospace"
      fontWeight="bold"
    >
      {payload?.value}
    </text>
  );
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: { payload: { stat: string; value: number; color: string } }[];
}

function RadarTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  const { stat, value, color } = payload[0].payload;
  return (
    <div className="rounded-lg border border-border bg-card-solid px-2.5 py-1 shadow-md text-xs">
      <span style={{ color }} className="font-mono font-bold">{stat}</span>
      <span className="text-text-dim ml-1.5">{value.toFixed(1)}</span>
    </div>
  );
}

export function StatRadar({
  cat,
  values,
  rangeMin,
  rangeMax,
  size = 140,
  showLabels = true,
}: StatRadarProps) {
  const data = cat
    ? catToRadarData(cat)
    : values
      ? valuesToRadarData(values)
      : valuesToRadarData([0, 0, 0, 0, 0, 0, 0]);

  const mergedData = data.map((d, i) => ({
    ...d,
    rangeMax: rangeMax?.[i] ?? 0,
    rangeMin: rangeMin?.[i] ?? 0,
  }));
  const hasRange = rangeMin && rangeMax;

  return (
    <div style={{ width: size, height: size }}>
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart
          data={mergedData}
          cx="50%"
          cy="50%"
          outerRadius={showLabels ? '68%' : '85%'}
        >
          <defs>
            <radialGradient id="radarFill" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="var(--color-good)" stopOpacity={0.6} />
              <stop offset="100%" stopColor="var(--color-good)" stopOpacity={0.1} />
            </radialGradient>
            <radialGradient id="rangeFill" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="var(--color-border)" stopOpacity={0.2} />
              <stop offset="100%" stopColor="var(--color-border)" stopOpacity={0.05} />
            </radialGradient>
          </defs>
          <PolarGrid
            stroke="var(--color-border)"
            strokeOpacity={0.3}
            strokeWidth={0.5}
          />
          {showLabels && (
            <PolarAngleAxis
              dataKey="stat"
              tick={CustomTick}
              tickLine={false}
            />
          )}
          {hasRange && (
            <Radar
              dataKey="rangeMax"
              fill="url(#rangeFill)"
              stroke="var(--color-border)"
              strokeWidth={0.5}
              strokeOpacity={0.4}
              isAnimationActive
              animationDuration={600}
            />
          )}
          <Radar
            dataKey="value"
            fill="url(#radarFill)"
            stroke="var(--color-good)"
            strokeWidth={1.5}
            dot={{
              r: 2.5,
              fill: 'var(--color-good)',
              stroke: 'var(--color-card-solid)',
              strokeWidth: 1,
            }}
            isAnimationActive
            animationDuration={800}
            animationEasing="ease-out"
          />
          {showLabels && <Tooltip content={<RadarTooltip />} />}
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
