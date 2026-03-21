import { motion } from 'framer-motion';
import { StatRadar } from '@/components/StatRadar';
import { ClassIcon } from '@/components/ClassIcon';
import { ScrollArea } from '@/components/ui/scroll-area';
import { setTeamSlot } from '@/bridge';
import type { SaveCat, CollarDef } from '@/types';

interface TopThreeListProps {
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

export function TopThreeList({ cats, collars }: TopThreeListProps) {
  const activeCats = cats.filter((c) => !c.retired);
  if (activeCats.length === 0 || collars.length === 0) {
    return <div className="text-center text-text-dim text-xs py-8">No cats</div>;
  }

  return (
    <ScrollArea className="h-[220px]">
      <div className="space-y-2 pr-2">
        {collars.map((collar, collarIdx) => {
          const scored = activeCats
            .map((cat) => ({ cat, score: collarScore(collar, cat) }))
            .sort((a, b) => b.score - a.score)
            .slice(0, 3);

          return (
            <motion.div
              key={collar.name}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: collarIdx * 0.03, duration: 0.3 }}
              className="flex items-center gap-2"
            >
              <ClassIcon name={collar.name} size={14} />

              <span
                className="text-[10px] font-mono font-bold w-12 shrink-0 truncate"
                style={{ color: collar.color }}
              >
                {collar.name.slice(0, 6)}
              </span>

              <div className="flex gap-1 flex-1 min-w-0">
                {scored.map(({ cat, score }) => (
                  <motion.button
                    key={cat.db_key}
                    whileHover={{ scale: 1.04, y: -1 }}
                    whileTap={{ scale: 0.97 }}
                    onClick={() => {
                      const emptySlot = [0, 1, 2, 3].find(() => true);
                      if (emptySlot !== undefined) {
                        setTeamSlot(emptySlot, cat.db_key, collar.name);
                      }
                    }}
                    className="flex items-center gap-1 rounded-md border border-border/50 bg-card px-1.5 py-0.5 cursor-pointer hover:bg-card-hover transition-colors min-w-0"
                  >
                    <StatRadar cat={cat} size={32} showLabels={false} />
                    <div className="min-w-0">
                      <div className="text-[10px] font-serif text-text truncate max-w-[60px]">
                        {cat.name}
                      </div>
                      <div
                        className="text-[9px] font-mono font-bold"
                        style={{ color: collar.color }}
                      >
                        {score.toFixed(1)}
                      </div>
                    </div>
                  </motion.button>
                ))}
              </div>
            </motion.div>
          );
        })}
      </div>
    </ScrollArea>
  );
}
