import { useMemo } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { STAT_LABELS, STAT_ORDER, type SaveCat } from '@/types';

const STATUS_LABELS: Record<string, string> = {
  in_house: 'In house',
  adventure: 'Adventure',
  historical: 'Historical',
  dead: 'Dead',
  unknown: 'Unknown',
};

const STATUS_COLORS: Record<string, string> = {
  in_house: '#3B7A57',
  adventure: '#4A90E2',
  historical: '#A67C52',
  dead: '#5C5C5C',
  unknown: '#888888',
};

function medianSorted(sorted: number[]): number {
  if (sorted.length === 0) return 0;
  const m = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[m]! : (sorted[m - 1]! + sorted[m]!) / 2;
}

function ChartCard({
  title,
  subtitle,
  children,
  chartHeight,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  chartHeight: number;
}) {
  return (
    <div className="parchment-card sketchy-border rounded-lg overflow-hidden p-3 mb-3">
      <h3 className="font-mono text-[11px] font-bold tracking-wider text-text uppercase mb-0.5">{title}</h3>
      {subtitle ? (
        <p className="text-[10px] text-text-dim mb-2 leading-snug">{subtitle}</p>
      ) : null}
      <div className="w-full" style={{ height: chartHeight }}>
        {children}
      </div>
    </div>
  );
}

const tooltipStyle = {
  backgroundColor: 'var(--card-solid, rgba(30,28,24,0.95))',
  border: '1px solid rgba(0,0,0,0.12)',
  borderRadius: '8px',
  fontSize: '11px',
  padding: '8px 10px',
};

function fmtCountTooltip(value: unknown) {
  const n = typeof value === 'number' ? value : Number(value);
  return [Number.isFinite(n) ? n : 0, 'Cats'] as const;
}

function fmtStatAggTooltip(value: unknown, name: unknown) {
  const n = typeof value === 'number' ? value : Number(value);
  const label = name === 'mean' ? 'Mean' : 'Median';
  return [Number.isFinite(n) ? n : 0, label] as const;
}

export function CatalogAnalyticsPanel({ cats }: { cats: SaveCat[] }) {
  const statusData = useMemo(() => {
    const counts = new Map<string, number>();
    for (const c of cats) {
      const k = c.status || 'unknown';
      counts.set(k, (counts.get(k) ?? 0) + 1);
    }
    return [...counts.entries()]
      .map(([status, count]) => ({
        key: status,
        label: STATUS_LABELS[status] ?? status.replace(/_/g, ' '),
        count,
      }))
      .sort((a, b) => b.count - a.count);
  }, [cats]);

  const generationData = useMemo(() => {
    const counts = new Map<number, number>();
    for (const c of cats) {
      const g = c.generation >= 21 ? 21 : Math.max(0, c.generation);
      counts.set(g, (counts.get(g) ?? 0) + 1);
    }
    return [...counts.entries()]
      .sort((a, b) => a[0] - b[0])
      .map(([gen, count]) => ({
        label: gen >= 21 ? '21+' : String(gen),
        count,
      }));
  }, [cats]);

  const genderData = useMemo(() => {
    const counts = new Map<string, number>();
    for (const c of cats) {
      const g = (c.gender || '').trim() || 'Unknown';
      counts.set(g, (counts.get(g) ?? 0) + 1);
    }
    return [...counts.entries()]
      .map(([gender, count]) => ({ label: gender, count }))
      .sort((a, b) => b.count - a.count);
  }, [cats]);

  const classData = useMemo(() => {
    const counts = new Map<string, number>();
    for (const c of cats) {
      const cl = (c.active_class || '').trim() || '(none)';
      counts.set(cl, (counts.get(cl) ?? 0) + 1);
    }
    return [...counts.entries()]
      .map(([cls, count]) => ({ label: cls, count }))
      .sort((a, b) => b.count - a.count);
  }, [cats]);

  const statAgg = useMemo(() => {
    return STAT_ORDER.map((key, i) => {
      const vals = cats.map((c) => c[`base_${key}` as keyof SaveCat] as number).sort((a, b) => a - b);
      const sum = vals.reduce((a, n) => a + n, 0);
      const mean = vals.length ? sum / vals.length : 0;
      const med = medianSorted(vals);
      return {
        name: STAT_LABELS[i]!,
        key,
        mean: Math.round(mean * 100) / 100,
        median: Math.round(med * 100) / 100,
      };
    });
  }, [cats]);

  const breedBins = useMemo(() => {
    const values = cats.map((c) => c.breed_coefficient);
    if (values.length === 0) return [];
    const max = Math.max(...values, 1e-6);
    const binCount = 16;
    const w = max / binCount;
    const bins = Array.from({ length: binCount }, (_, i) => {
      const lo = i * w;
      const hi = (i + 1) * w;
      return {
        label: `${lo.toFixed(2)}–${hi.toFixed(2)}`,
        count: 0,
        lo,
        hi,
      };
    });
    for (const v of values) {
      let idx = Math.floor(v / w);
      if (idx >= binCount) idx = binCount - 1;
      if (idx < 0) idx = 0;
      bins[idx]!.count++;
    }
    return bins;
  }, [cats]);

  if (cats.length === 0) {
    return (
      <div className="parchment-empty rounded-lg flex flex-col items-center justify-center gap-2 py-12 px-4">
        <span className="text-[11px] font-mono font-bold text-text-dim tracking-wider">No catalog data</span>
        <span className="text-[10px] text-text-dim text-center max-w-[260px] leading-relaxed">
          Load a save in Mewgent to see every cat record from the file.
        </span>
      </div>
    );
  }

  const statusH = Math.max(140, statusData.length * 32 + 48);
  const genderH = Math.max(120, genderData.length * 28 + 48);
  const classH = Math.max(160, Math.min(classData.length * 24 + 56, 360));

  return (
    <div className="flex flex-col gap-1 pb-4">
      <p className="text-[10px] text-text-dim font-mono mb-1 px-0.5 leading-relaxed">
        Lifetime snapshot: {cats.length} records (includes empty or deceased rows — expect zeros in stats /
        breed coefficient).
      </p>

      <ChartCard
        title="Status"
        subtitle="In house, on adventure, historical ledger, or dead (save heuristics)."
        chartHeight={statusH}
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={statusData}
            layout="vertical"
            margin={{ left: 4, right: 12, top: 8, bottom: 8 }}
          >
            <CartesianGrid strokeDasharray="3 3" className="stroke-border/40" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }} />
            <YAxis
              dataKey="label"
              type="category"
              width={92}
              tick={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              cursor={{ fill: 'rgba(0,0,0,0.04)' }}
              contentStyle={tooltipStyle}
              formatter={fmtCountTooltip}
            />
            <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={18} isAnimationActive={false}>
              {statusData.map((d) => (
                <Cell key={d.key} fill={STATUS_COLORS[d.key] ?? STATUS_COLORS.unknown} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard
        title="Generation"
        subtitle="Breeding depth; 21+ buckets long lineages."
        chartHeight={200}
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={generationData} margin={{ left: 4, right: 8, top: 8, bottom: 28 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border/40" />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}
              interval={0}
              angle={-25}
              textAnchor="end"
              height={48}
            />
            <YAxis tick={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }} allowDecimals={false} />
            <Tooltip contentStyle={tooltipStyle} formatter={fmtCountTooltip} />
            <Bar dataKey="count" fill="#6B5B95" radius={[4, 4, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="Gender" chartHeight={genderH}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={genderData}
            layout="vertical"
            margin={{ left: 4, right: 12, top: 8, bottom: 8 }}
          >
            <CartesianGrid strokeDasharray="3 3" className="stroke-border/40" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }} />
            <YAxis
              dataKey="label"
              type="category"
              width={72}
              tick={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip contentStyle={tooltipStyle} formatter={fmtCountTooltip} />
            <Bar dataKey="count" fill="#C17070" radius={[0, 4, 4, 0]} barSize={16} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="Class" subtitle="Active class across all records; (none) if unset." chartHeight={classH}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={classData}
            layout="vertical"
            margin={{ left: 4, right: 12, top: 8, bottom: 8 }}
          >
            <CartesianGrid strokeDasharray="3 3" className="stroke-border/40" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }} />
            <YAxis
              dataKey="label"
              type="category"
              width={88}
              tick={{ fontSize: 9, fontFamily: 'JetBrains Mono, monospace' }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip contentStyle={tooltipStyle} formatter={fmtCountTooltip} />
            <Bar dataKey="count" fill="#4A90E2" radius={[0, 4, 4, 0]} barSize={14} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard
        title="Base stats (population)"
        subtitle="Mean vs median per stat — includes stub / dead zeros."
        chartHeight={220}
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={statAgg} margin={{ left: 4, right: 8, top: 8, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border/40" />
            <XAxis dataKey="name" tick={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace', fontWeight: 700 }} />
            <YAxis tick={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }} />
            <Tooltip contentStyle={tooltipStyle} formatter={fmtStatAggTooltip} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Bar dataKey="mean" fill="#C13128" radius={[4, 4, 0, 0]} name="Mean" isAnimationActive={false} />
            <Bar dataKey="median" fill="#3B7A57" radius={[4, 4, 0, 0]} name="Median" isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard
        title="Breed coefficient"
        subtitle="Distribution across all records (wider spread = more diverse coefficients)."
        chartHeight={220}
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={breedBins} margin={{ left: 4, right: 8, top: 8, bottom: 36 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border/40" />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 8, fontFamily: 'JetBrains Mono, monospace' }}
              interval={0}
              angle={-40}
              textAnchor="end"
              height={58}
            />
            <YAxis tick={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }} allowDecimals={false} />
            <Tooltip contentStyle={tooltipStyle} formatter={fmtCountTooltip} />
            <Bar dataKey="count" fill="#D4A017" radius={[4, 4, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}
