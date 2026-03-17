import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { classIconUrl } from '@/components/ClassIcon';
import type { SaveCat, CollarDef } from '@/types';

interface ClassFitProps {
  cats: SaveCat[];
  collars: CollarDef[];
}

const STAT_KEYS = ['str', 'dex', 'con', 'int', 'spd', 'cha', 'lck'] as const;

function collarScore(collar: CollarDef, cat: SaveCat): number {
  let total = 0;
  let norm = 0;
  for (let i = 0; i < STAT_KEYS.length; i++) {
    const val = cat[`base_${STAT_KEYS[i]}` as keyof SaveCat] as number;
    const w = collar.score_weights[i] ?? 0;
    total += val * w;
    norm += Math.abs(w);
  }
  return norm > 0 ? total / norm : 0;
}

function computeClassFit(cats: SaveCat[], collars: CollarDef[]) {
  return collars.map((collar) => {
    let good = 0, ok = 0, poor = 0;
    for (const cat of cats) {
      const sc = collarScore(collar, cat);
      if (sc >= 7.0) good++;
      else if (sc >= 5.0) ok++;
      else poor++;
    }
    return {
      name: collar.name.slice(0, 7),
      fullName: collar.name,
      color: collar.color,
      good,
      ok,
      poor,
    };
  });
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function ClassAxisTick(props: any) {
  const { x, y, payload } = props;
  const name = payload?.value as string;
  const entry = props.visibleTicksCount ? undefined : undefined;
  void entry;
  const iconUrl = classIconUrl(name);
  return (
    <g transform={`translate(${x},${y})`}>
      {iconUrl && (
        <image
          href={iconUrl}
          x={-50}
          y={-7}
          width={14}
          height={14}
        />
      )}
      <text
        x={-32}
        y={0}
        dy={4}
        textAnchor="start"
        fontSize={9}
        fontFamily="'JetBrains Mono', monospace"
        fontWeight="bold"
        fill="var(--color-text)"
      >
        {name}
      </text>
    </g>
  );
}

interface FitTooltipProps {
  active?: boolean;
  payload?: { payload: { fullName: string; color: string; good: number; ok: number; poor: number } }[];
}

function ClassFitTooltip({ active, payload }: FitTooltipProps) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  const iconUrl = classIconUrl(d.fullName);
  return (
    <div className="rounded-lg border border-border bg-card-solid px-3 py-2 shadow-md text-xs">
      <div className="flex items-center gap-1.5 font-mono font-bold mb-1" style={{ color: d.color }}>
        {iconUrl && <img src={iconUrl} alt="" width={14} height={14} />}
        {d.fullName}
      </div>
      <div className="space-y-0.5 text-text-dim">
        <div>Good (7+): <span className="font-mono text-good">{d.good}</span></div>
        <div>OK (5-7): <span className="font-mono text-medium">{d.ok}</span></div>
        <div>Poor (&lt;5): <span className="font-mono text-poor">{d.poor}</span></div>
      </div>
    </div>
  );
}

export function ClassFit({ cats, collars }: ClassFitProps) {
  if (cats.length === 0 || collars.length === 0) {
    return <div className="text-center text-text-dim text-xs py-8 font-serif">No cats</div>;
  }

  const data = computeClassFit(cats, collars);

  return (
    <div className="w-full" style={{ height: Math.max(120, data.length * 26 + 20) }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 4, right: 8, top: 4, bottom: 4 }}>
          <XAxis type="number" hide domain={[0, cats.length]} />
          <YAxis
            dataKey="name"
            type="category"
            width={68}
            tick={ClassAxisTick}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<ClassFitTooltip />} />
          <Bar dataKey="poor" stackId="a" barSize={13} isAnimationActive animationDuration={600}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.color} fillOpacity={0.2} />
            ))}
          </Bar>
          <Bar dataKey="ok" stackId="a" barSize={13} isAnimationActive animationDuration={700}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.color} fillOpacity={0.5} />
            ))}
          </Bar>
          <Bar dataKey="good" stackId="a" radius={[0, 4, 4, 0]} barSize={13} isAnimationActive animationDuration={800}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.color} fillOpacity={0.9} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
