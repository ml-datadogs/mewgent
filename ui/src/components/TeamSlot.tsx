import { motion } from 'framer-motion';
import { ClassIcon } from '@/components/ClassIcon';
import { useAnimatedNumber } from '@/hooks/useAnimatedNumber';
import { StashTipWithTooltip } from '@/components/StashTipWithTooltip';
import type { TeamStashTip } from '@/bridge';
import { STAT_ORDER, STAT_LABELS, STAT_COLORS } from '@/types';
import type { TeamSlot as TeamSlotType, CollarDef, SaveCat, StatKey } from '@/types';

const CARD_TILTS = [-1.2, 0.8, -0.6, 1.1, -0.9, 0.5];

interface TeamSlotProps {
  index: number;
  slot: TeamSlotType | null;
  collars: CollarDef[];
  /** LLM stash suggestions for this cat (matched by name). */
  suggestedStashTips?: TeamStashTip[];
}

function ScoreBadge({ value }: { value: number }) {
  const animated = useAnimatedNumber(value);
  return (
    <div
      className="sketchy-frame flex items-center justify-center rounded-sm px-1.5 py-0.5"
      style={{ background: 'rgba(255,255,255,0.35)' }}
    >
      <motion.span className="font-mono text-[11px] font-bold text-accent tabular-nums leading-none">
        {animated}
      </motion.span>
    </div>
  );
}

function StatGrid({ cat, collar }: { cat: SaveCat; collar: CollarDef | undefined }) {
  const weights = collar?.score_weights ?? [];
  const maxWeight = Math.max(...weights, 0);
  const threshold = maxWeight * 0.6;

  const left = STAT_ORDER.slice(0, 4);
  const right = STAT_ORDER.slice(4);

  function renderStat(key: string, i: number) {
    const value = cat[`base_${key}` as keyof SaveCat] as number;
    const weight = weights[i] ?? 0;
    const isKey = weight >= threshold && weight > 0;
    const color = STAT_COLORS[key as StatKey];

    return (
      <motion.div
        key={key}
        initial={{ opacity: 0, x: -4 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.15, delay: i * 0.03 }}
        className="flex items-center justify-between gap-1 px-1 py-px rounded-sm"
        style={{
          backgroundColor: isKey ? `color-mix(in srgb, ${color} 12%, transparent)` : undefined,
        }}
      >
        <span
          className="text-[9px] font-mono font-bold leading-none tracking-wider"
          style={{ color: isKey ? color : 'var(--color-text-dim)', opacity: isKey ? 1 : 0.55 }}
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
  }

  return (
    <div className="grid grid-cols-2 gap-x-2 gap-y-0">
      <div className="flex flex-col gap-0.5">
        {left.map((key, i) => renderStat(key, i))}
      </div>
      <div className="flex flex-col gap-0.5">
        {right.map((key, i) => renderStat(key, i + 4))}
      </div>
    </div>
  );
}

function SuggestedStashRow({ tips, catName }: { tips: TeamStashTip[]; catName: string }) {
  if (tips.length === 0) return null;
  return (
    <div className="mt-1.5">
      <span className="text-[8px] font-mono font-bold text-text-dim tracking-wider block mb-0.5">
        AI stash
      </span>
      <div className="flex items-center gap-1 flex-wrap">
        {tips.map((tip) => (
          <StashTipWithTooltip
            key={`${tip.item_id}-${tip.reason.slice(0, 24)}`}
            tip={tip}
            forCatName={catName}
          />
        ))}
      </div>
    </div>
  );
}

export function TeamSlotCard({ index, slot, collars, suggestedStashTips = [] }: TeamSlotProps) {
  const isEmpty = slot === null;
  const tilt = CARD_TILTS[index % CARD_TILTS.length];

  const currentCollar = collars.find((c) => c.name === slot?.collar_name);
  const collarColor = currentCollar?.color ?? 'var(--color-border)';

  if (isEmpty) {
    return (
      <motion.div
        layout
        initial={{ opacity: 0 }}
        animate={{ opacity: 0.4 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2, delay: index * 0.04 }}
        className="parchment-empty rounded-lg py-5 px-4 flex flex-col items-center justify-center gap-1"
        style={{ transform: `rotate(${tilt * 0.5}deg)` }}
      >
        <span className="text-[11px] font-mono font-bold text-text-dim tracking-wider opacity-50">
          SLOT {index + 1}
        </span>
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
      whileHover={{
        y: -3,
        rotate: 0,
        boxShadow: '0 8px 20px rgba(0,0,0,0.12)',
        transition: { duration: 0.2 },
      }}
      className="parchment-card card-tape sketchy-border rounded-lg overflow-hidden"
      style={{
        '--card-bg': `color-mix(in srgb, ${collarColor} 6%, var(--color-card-solid))`,
        transform: `rotate(${tilt}deg)`,
        paddingBottom: '4px',
        borderLeft: `3px solid ${collarColor}`,
      } as React.CSSProperties}
    >
      <div className="px-2.5 pt-2.5 pb-2">
        {/* Header: Name + Level + Score */}
        <motion.div
          initial={{ opacity: 0, x: -6 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.25, delay: index * 0.08 + 0.1 }}
          className="flex items-start justify-between mb-1.5"
        >
          <div className="min-w-0 flex-1">
            <h3 className="text-[13px] font-serif font-bold text-text truncate leading-tight">
              {slot.cat.name}
            </h3>
            <span className="text-[10px] font-mono text-text-dim">
              Lv.{slot.cat.level}
            </span>
          </div>
          <ScoreBadge value={slot.score} />
        </motion.div>

        {/* Framed class icon + stats */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3, delay: index * 0.08 + 0.15 }}
          className="flex gap-2 items-start"
        >
          {/* Class icon in sketchy frame */}
          <div
            className="sketchy-frame rounded-sm p-1 shrink-0 flex items-center justify-center"
            style={{
              background: `color-mix(in srgb, ${collarColor} 8%, rgba(255,255,255,0.4))`,
              transform: 'rotate(-1deg)',
            }}
          >
            <ClassIcon name={slot.collar_name} size={26} />
          </div>

          {/* 2-column stat grid */}
          <div className="flex-1 min-w-0">
            <StatGrid cat={slot.cat} collar={currentCollar} />
          </div>
        </motion.div>

        <SuggestedStashRow tips={suggestedStashTips} catName={slot.cat.name} />

        {/* Explanation */}
        {slot.explanation && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4, delay: index * 0.08 + 0.3 }}
          >
            <div
              className="h-px mt-2 mb-1.5 mx-1"
              style={{
                background: 'repeating-linear-gradient(90deg, var(--color-border-subtle) 0px, var(--color-border-subtle) 3px, transparent 3px, transparent 6px)',
              }}
            />
            <p className="text-[10px] text-text-dim italic leading-snug px-0.5">
              {slot.explanation}
            </p>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}
