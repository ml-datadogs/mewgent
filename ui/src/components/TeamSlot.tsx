import { motion } from 'framer-motion';
import { ClassIcon } from '@/components/ClassIcon';
import { useAnimatedNumber } from '@/hooks/useAnimatedNumber';
import { STAT_ORDER, STAT_LABELS, STAT_COLORS } from '@/types';
import type { TeamSlot as TeamSlotType, CollarDef, SaveCat, StatKey } from '@/types';

interface TeamSlotProps {
  index: number;
  slot: TeamSlotType | null;
  collars: CollarDef[];
}

function ScoreDisplay({ value }: { value: number }) {
  const animated = useAnimatedNumber(value);
  return (
    <motion.span className="font-mono text-sm font-bold text-accent tabular-nums">
      {animated}
    </motion.span>
  );
}

function StatGrid({ cat, collar }: { cat: SaveCat; collar: CollarDef | undefined }) {
  const weights = collar?.score_weights ?? [];
  const maxWeight = Math.max(...weights, 0);
  const threshold = maxWeight * 0.6;

  return (
    <div className="grid grid-cols-4 gap-x-1.5 gap-y-1">
      {STAT_ORDER.map((key, i) => {
        const value = cat[`base_${key}` as keyof SaveCat] as number;
        const weight = weights[i] ?? 0;
        const isKey = weight >= threshold && weight > 0;
        const color = STAT_COLORS[key as StatKey];

        return (
          <motion.div
            key={key}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.2, delay: i * 0.03 }}
            className="flex items-center gap-1 rounded-md px-1 py-0.5"
            style={{
              backgroundColor: isKey ? `color-mix(in srgb, ${color} 15%, transparent)` : undefined,
            }}
          >
            <span
              className="text-[9px] font-mono font-bold leading-none"
              style={{ color: isKey ? color : 'var(--color-text-dim)', opacity: isKey ? 1 : 0.6 }}
            >
              {STAT_LABELS[i]}
            </span>
            <span
              className="text-[11px] font-mono font-bold tabular-nums leading-none"
              style={{ color: isKey ? color : 'var(--color-text)' }}
            >
              {value}
            </span>
          </motion.div>
        );
      })}
    </div>
  );
}

export function TeamSlotCard({ index, slot, collars }: TeamSlotProps) {
  const isEmpty = slot === null;

  const currentCollar = collars.find((c) => c.name === slot?.collar_name);
  const collarColor = currentCollar?.color ?? 'var(--color-border)';

  if (isEmpty) {
    return (
      <motion.div
        layout
        initial={{ opacity: 0 }}
        animate={{ opacity: 0.5 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2, delay: index * 0.04 }}
        className="rounded-xl border border-border-subtle py-4 px-4 flex items-center justify-center"
      >
        <span className="text-xs text-text-dim italic">Slot {index + 1}</span>
      </motion.div>
    );
  }

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ type: 'spring', stiffness: 300, damping: 26, delay: index * 0.08 }}
      whileHover={{ y: -2, boxShadow: '0 8px 24px rgba(0,0,0,0.12)' }}
      className="rounded-xl overflow-hidden transition-shadow duration-200"
      style={{
        border: `1px solid color-mix(in srgb, ${collarColor} 30%, var(--color-border))`,
        boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
      }}
    >
      <div className="h-1" style={{ background: collarColor }} />

      <div
        className="px-3 pt-2.5 pb-2.5"
        style={{
          background: `linear-gradient(180deg, color-mix(in srgb, ${collarColor} 8%, var(--color-card)) 0%, var(--color-card) 100%)`,
        }}
      >
        <motion.div
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3, delay: index * 0.08 + 0.1 }}
          className="flex items-start justify-between mb-2"
        >
          <div className="min-w-0">
            <h3 className="text-sm font-serif font-bold text-text truncate leading-tight">
              {slot.cat.name}
            </h3>
            <div className="flex items-center gap-1 mt-0.5">
              <ClassIcon name={slot.collar_name} size={12} />
              <span
                className="text-[10px] font-mono font-semibold"
                style={{ color: collarColor }}
              >
                {slot.collar_name}
              </span>
            </div>
          </div>
          <ScoreDisplay value={slot.score} />
        </motion.div>

        <StatGrid cat={slot.cat} collar={currentCollar} />

        {slot.explanation && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4, delay: index * 0.08 + 0.3 }}
          >
            <div className="h-px bg-border-subtle mt-2 mb-1.5" />
            <p className="text-[10px] text-text-dim italic leading-snug">
              {slot.explanation}
            </p>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}
