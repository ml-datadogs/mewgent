import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { TeamSlotCard } from '@/components/TeamSlot';
import { AiProgressStepper } from '@/components/AiProgressStepper';
import { autofillTeam, autofillTeamLlm, clearTeam, setTeamSlot } from '@/bridge';
import { useAnimatedNumber } from '@/hooks/useAnimatedNumber';
import type { TeamSlot, CollarDef } from '@/types';

interface TeamPanelProps {
  team: (TeamSlot | null)[];
  collars: CollarDef[];
  llmStatus: string;
  llmAvailable: boolean;
  teamSynergy: string;
}

function TeamScore({ value }: { value: number }) {
  const animated = useAnimatedNumber(value);
  return (
    <motion.span className="font-mono text-xs font-bold text-accent tabular-nums">
      Score: {value > 0 ? animated : '--'}
    </motion.span>
  );
}

export function TeamPanel({ team, collars, llmStatus, llmAvailable, teamSynergy }: TeamPanelProps) {
  const totalScore = team.reduce((sum, s) => sum + (s?.score ?? 0), 0);

  const handleClassChange = (slotIdx: number, collarName: string) => {
    const slot = team[slotIdx];
    if (slot) {
      setTeamSlot(slotIdx, slot.cat.db_key, collarName);
    }
  };

  return (
    <Card>
      <CardContent className="p-2.5">
        <div className="flex items-center gap-2 mb-2">
          <span className="font-mono text-xs font-bold text-accent tracking-wider">
            TEAM
          </span>
          <div className="flex-1" />
          <TeamScore value={totalScore} />
        </div>

        <div className="space-y-1">
          <AnimatePresence mode="popLayout">
            {team.map((slot, i) => (
              <TeamSlotCard
                key={`slot-${i}`}
                index={i}
                slot={slot}
                collars={collars}
                onClassChange={handleClassChange}
              />
            ))}
          </AnimatePresence>
        </div>

        <AnimatePresence>
          {teamSynergy && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.25 }}
              className="overflow-hidden"
            >
              <p className="text-[10px] text-text-dim font-serif italic leading-snug mt-1.5 px-1">
                {teamSynergy}
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="flex items-center justify-center gap-2 mt-2.5">
          <Button onClick={autofillTeam}>
            Auto-fill best team
          </Button>

          {llmAvailable && (
            <Button
              variant="default"
              onClick={autofillTeamLlm}
              disabled={!!llmStatus}
            >
              AI Team
            </Button>
          )}

          <Button variant="destructive" onClick={clearTeam}>
            Clear
          </Button>
        </div>

        <AiProgressStepper active={!!llmStatus} />
      </CardContent>
    </Card>
  );
}
