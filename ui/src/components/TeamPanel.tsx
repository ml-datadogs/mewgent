import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { TeamSlotCard } from '@/components/TeamSlot';
import { AiCircleProgress } from '@/components/AiCircleProgress';
import { clearTeam } from '@/bridge';
import { useAnimatedNumber } from '@/hooks/useAnimatedNumber';
import type { TeamSlot, CollarDef } from '@/types';

interface TeamPanelProps {
  team: (TeamSlot | null)[];
  collars: CollarDef[];
  llmStatus: string;
  llmAvailable: boolean;
  bridgeConnected: boolean;
  teamSynergy: string;
}

function TeamScore({ value }: { value: number }) {
  const animated = useAnimatedNumber(value);
  return (
    <motion.span className="font-mono text-sm font-bold text-accent tabular-nums">
      {value > 0 ? animated : '--'}
    </motion.span>
  );
}

export function TeamPanel({
  team,
  collars,
  llmStatus,
  bridgeConnected,
  teamSynergy,
}: TeamPanelProps) {
  const totalScore = team.reduce((sum, s) => sum + (s?.score ?? 0), 0);
  const isLoading = !!llmStatus;
  const hasTeam = team.some((s) => s !== null);

  return (
    <div
      className={`flex flex-col gap-3 py-1${isLoading ? ' min-h-full h-full' : ''}`}
    >
      <div className="flex items-center gap-2 px-1">
        <span className="font-mono text-xs font-bold text-accent tracking-wider">
          TEAM
        </span>
        <div className="flex-1" />
        {!isLoading && <TeamScore value={totalScore} />}
      </div>

      <AnimatePresence mode="wait">
        {isLoading ? (
          <motion.div
            key="spinner"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="flex-1 flex items-center justify-center"
          >
            <AiCircleProgress active={isLoading} />
          </motion.div>
        ) : (
          <motion.div
            key="cards"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="grid grid-cols-2 gap-3 pt-2"
          >
            <AnimatePresence mode="popLayout">
              {team.map((slot, i) => (
                <TeamSlotCard
                  key={`slot-${i}`}
                  index={i}
                  slot={slot}
                  collars={collars}
                />
              ))}
            </AnimatePresence>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {teamSynergy && !isLoading && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <p className="text-xs text-text-dim italic leading-snug px-1">
              {teamSynergy}
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {hasTeam && !isLoading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="flex items-center justify-center"
        >
          <Button
            variant="ghost"
            onClick={clearTeam}
            disabled={!bridgeConnected}
            title={!bridgeConnected ? 'Requires Mewgent app' : undefined}
          >
            Clear
          </Button>
        </motion.div>
      )}
    </div>
  );
}
