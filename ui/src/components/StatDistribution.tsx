import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { STAT_ORDER, STAT_LABELS, STAT_COLORS, type SaveCat, type StatKey } from '@/types';

interface StatDistributionProps {
  cats: SaveCat[];
}

function computeDistribution(cats: SaveCat[]) {
  return STAT_ORDER.map((key, i) => {
    let low = 0, mid = 0, high = 0;
    for (const cat of cats) {
      const val = cat[`base_${key}` as keyof SaveCat] as number;
      if (val <= 3) low++;
      else if (val <= 6) mid++;
      else high++;
    }
    return {
      stat: STAT_LABELS[i],
      key,
      low,
      mid,
      high,
      total: cats.length,
    };
  });
}

interface DistTooltipProps {
  active?: boolean;
  payload?: { payload: { stat: string; low: number; mid: number; high: number; total: number; key: string } }[];
}

function DistributionTooltip({ active, payload }: DistTooltipProps) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  const color = STAT_COLORS[d.key as StatKey];
  return (
    <div className="rounded-lg border border-border bg-card-solid px-3 py-2 shadow-md text-xs">
      <div className="font-mono font-bold mb-1" style={{ color }}>{d.stat}</div>
      <div className="space-y-0.5 text-text-dim">
        <div>Low (0-3): <span className="font-mono text-text">{d.low}</span></div>
        <div>Mid (4-6): <span className="font-mono text-text">{d.mid}</span></div>
        <div>High (7+): <span className="font-mono text-text">{d.high}</span></div>
      </div>
    </div>
  );
}

export function StatDistribution({ cats }: StatDistributionProps) {
  if (cats.length === 0) {
    return <div className="text-center text-text-dim text-xs py-8 font-serif">No cats</div>;
  }

  const data = computeDistribution(cats);

  return (
    <div className="w-full" style={{ height: Math.max(160, data.length * 28 + 20) }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 4, right: 8, top: 4, bottom: 4 }}>
          <XAxis type="number" hide domain={[0, cats.length]} />
          <YAxis
            dataKey="stat"
            type="category"
            width={36}
            tick={{ fontSize: 10, fontFamily: "'JetBrains Mono', monospace", fontWeight: 'bold' }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<DistributionTooltip />} />
          <Bar dataKey="low" stackId="a" radius={[0, 0, 0, 0]} barSize={14} isAnimationActive animationDuration={600}>
            {data.map((d) => (
              <Cell key={d.key} fill={STAT_COLORS[d.key as StatKey]} fillOpacity={0.25} />
            ))}
          </Bar>
          <Bar dataKey="mid" stackId="a" radius={[0, 0, 0, 0]} barSize={14} isAnimationActive animationDuration={700}>
            {data.map((d) => (
              <Cell key={d.key} fill={STAT_COLORS[d.key as StatKey]} fillOpacity={0.55} />
            ))}
          </Bar>
          <Bar dataKey="high" stackId="a" radius={[0, 4, 4, 0]} barSize={14} isAnimationActive animationDuration={800}>
            {data.map((d) => (
              <Cell key={d.key} fill={STAT_COLORS[d.key as StatKey]} fillOpacity={0.9} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
