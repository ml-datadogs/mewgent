import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { StashTipWithTooltip } from '@/components/StashTipWithTooltip';
import { TeamSlotCard } from '@/components/TeamSlot';
import { AiCircleProgress } from '@/components/AiCircleProgress';
import { clearTeam } from '@/bridge';
import type { TeamStashTip, TeamSynergyPayload } from '@/bridge';
import { useAnimatedNumber } from '@/hooks/useAnimatedNumber';
import type { TeamSlot, CollarDef } from '@/types';

function stashTipTargetsCat(tip: TeamStashTip, catName: string): boolean {
  const on = tip.equip_on.trim().toLowerCase();
  if (!on || on === 'flex') return false;
  const name = catName.trim().toLowerCase();
  if (on === name) return true;
  return name.includes(on) || on.includes(name);
}

interface TeamPanelProps {
  team: (TeamSlot | null)[];
  collars: CollarDef[];
  llmStatus: string;
  bridgeConnected: boolean;
  teamSynergy: TeamSynergyPayload;
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
  const { synergy, stash_tips } = teamSynergy;
  const flexStashTips = stash_tips.filter(
    (t) => !t.equip_on.trim() || t.equip_on.trim().toLowerCase() === 'flex',
  );
  const showSynergySection =
    !isLoading && (synergy.trim().length > 0 || stash_tips.length > 0);

  return (
    <div
      className={`flex flex-col gap-3 py-1${isLoading ? ' min-h-full h-full' : ''}`}
    >
      <div className="flex items-center gap-2 px-1 flex-wrap">
        <span className="font-mono text-xs font-bold text-accent tracking-wider">
          TEAM
        </span>
        <div className="flex-1 min-w-[1rem]" />
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
                  suggestedStashTips={
                    slot
                      ? stash_tips.filter((t) => stashTipTargetsCat(t, slot.cat.name))
                      : []
                  }
                />
              ))}
            </AnimatePresence>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {showSynergySection && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden space-y-2 px-1"
          >
            {synergy.trim().length > 0 && (
              <p className="text-xs text-text-dim italic leading-snug">{synergy}</p>
            )}
            {flexStashTips.length > 0 && (
              <div>
                <span className="text-[8px] font-mono font-bold text-text-dim tracking-wider block mb-1">
                  Open picks
                </span>
                <div className="flex flex-wrap gap-1">
                  {flexStashTips.map((tip) => (
                    <StashTipWithTooltip
                      key={`flex-${tip.item_id}-${tip.reason.slice(0, 20)}`}
                      tip={tip}
                      size="lg"
                      hint="Open pick — assign to whichever cat fits your comp."
                      frameStyle={{ background: 'rgba(255,255,255,0.4)' }}
                    />
                  ))}
                </div>
              </div>
            )}
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
