import { motion } from 'framer-motion';
import { StatRadar } from '@/components/StatRadar';
import { ClassIcon } from '@/components/ClassIcon';
import { useAnimatedNumber } from '@/hooks/useAnimatedNumber';
import { removeTeamSlot } from '@/bridge';
import type { TeamSlot as TeamSlotType, CollarDef } from '@/types';

interface TeamSlotProps {
  index: number;
  slot: TeamSlotType | null;
  collars: CollarDef[];
  onClassChange: (slotIdx: number, collarName: string) => void;
}

function ScoreDisplay({ value }: { value: number }) {
  const animated = useAnimatedNumber(value);
  return (
    <motion.span className="font-mono text-sm font-bold text-accent tabular-nums">
      {animated}
    </motion.span>
  );
}

export function TeamSlotCard({ index, slot, collars, onClassChange }: TeamSlotProps) {
  const isEmpty = slot === null;

  const currentCollar = collars.find((c) => c.name === slot?.collar_name);
  const borderColor = currentCollar?.color ?? 'transparent';

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95, y: -8 }}
      transition={{ type: 'spring', stiffness: 350, damping: 28, delay: index * 0.04 }}
      whileHover={!isEmpty ? { scale: 1.01, boxShadow: '0 4px 16px rgba(0,0,0,0.08)' } : undefined}
      className="rounded-lg transition-colors duration-200"
      style={{
        borderLeft: `3px solid ${isEmpty ? 'transparent' : borderColor}`,
        backgroundColor: isEmpty ? 'transparent' : 'var(--color-highlight)',
        padding: '4px 8px',
      }}
    >
      <div className="flex items-center gap-2">
        <span className="font-mono text-xs font-bold text-text-dim w-4 text-right shrink-0">
          {index + 1}.
        </span>

        {!isEmpty && slot.cat && (
          <motion.div
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: 'spring', stiffness: 400, damping: 25 }}
          >
            <StatRadar cat={slot.cat} size={44} showLabels={false} />
          </motion.div>
        )}

        <div className="flex-1 min-w-0">
          {isEmpty ? (
            <span className="text-xs text-text-dim font-serif italic">(empty)</span>
          ) : (
            <motion.span
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-xs font-serif font-bold text-text truncate block"
            >
              {slot.cat.name}
            </motion.span>
          )}
        </div>

        {!isEmpty && (
          <>
            <ClassIcon name={slot.collar_name} size={16} />

            <select
              value={slot.collar_name}
              onChange={(e) => onClassChange(index, e.target.value)}
              className="h-5 px-1.5 text-[10px] font-mono rounded border border-border bg-bg-dim text-text cursor-pointer focus:outline-none focus:ring-1 focus:ring-border"
            >
              {collars.map((c) => (
                <option key={c.name} value={c.name}>
                  {c.name}
                </option>
              ))}
            </select>

            <ScoreDisplay value={slot.score} />

            <motion.button
              whileHover={{ scale: 1.2, color: 'var(--color-accent)' }}
              whileTap={{ scale: 0.85 }}
              onClick={() => removeTeamSlot(index)}
              className="w-4 h-4 flex items-center justify-center text-[10px] text-text-dim cursor-pointer rounded-full hover:bg-black/5 transition-colors"
            >
              ✕
            </motion.button>
          </>
        )}
      </div>

      {!isEmpty && slot.explanation && (
        <motion.p
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="text-[10px] text-text-dim mt-1 ml-6 italic leading-tight"
        >
          {slot.explanation}
        </motion.p>
      )}
    </motion.div>
  );
}
