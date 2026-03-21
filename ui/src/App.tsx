import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { TooltipProvider } from '@/components/ui/tooltip';
import { TitleBar } from '@/components/TitleBar';
import { HomeCarousel, type AppMode } from '@/components/HomeCarousel';
import { TeamPanel } from '@/components/TeamPanel';
import { Overview } from '@/components/Overview';
import { BreedingPanel } from '@/components/BreedingPanel';
import { StatusBar } from '@/components/StatusBar';
import { UpdateBanner } from '@/components/UpdateBanner';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useBridge } from '@/hooks/useBridge';

const pageVariants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -16 },
};

export default function App() {
  const { roster, collars, team, teamSynergy, saveInfo, llmStatus, updateInfo } = useBridge();
  const [mode, setMode] = useState<'home' | AppMode>('home');
  const cats = roster.map((r) => r.cat);

  const goHome = () => setMode('home');

  return (
    <TooltipProvider>
      <div className="h-full w-full p-0">
        {mode === 'home' ? (
          <div className="h-full w-full overflow-hidden">
            <HomeCarousel
              onSelect={setMode}
              day={saveInfo.day}
              catCount={saveInfo.cat_count}
            />
          </div>
        ) : (
        <div
          className="h-full w-full rounded-lg border-2 border-border bg-paper flex flex-col overflow-hidden"
          style={{ boxShadow: '0 8px 32px rgba(0,0,0,0.18)' }}
        >
          <div className="flex flex-col gap-1.5 p-3 flex-1 overflow-hidden">
            <TitleBar
              day={saveInfo.day}
              catCount={saveInfo.cat_count}
              onBack={goHome}
            />

            <div className="h-px bg-border shrink-0" />

            {updateInfo && <UpdateBanner info={updateInfo} />}

            <AnimatePresence mode="wait">
              {mode === 'breeding' && (
                <motion.div
                  key="breeding"
                  variants={pageVariants}
                  initial="initial"
                  animate="animate"
                  exit="exit"
                  transition={{ duration: 0.25 }}
                  className="flex-1 min-h-0 overflow-auto"
                >
                  <ScrollArea className="h-full">
                    <div className="pr-1">
                      {cats.length >= 2 ? (
                        <BreedingPanel cats={cats} collars={collars} llmAvailable={collars.length > 0} />
                      ) : (
                        <div className="flex items-center justify-center h-[200px] text-text-dim text-xs font-serif">
                          Need at least 2 cats to analyze breeding
                        </div>
                      )}
                    </div>
                  </ScrollArea>
                </motion.div>
              )}

              {mode === 'team' && (
                <motion.div
                  key="team"
                  variants={pageVariants}
                  initial="initial"
                  animate="animate"
                  exit="exit"
                  transition={{ duration: 0.25 }}
                  className="flex-1 min-h-0 flex flex-col overflow-hidden"
                >
                  <TeamPanel
                    team={team}
                    collars={collars}
                    llmStatus={llmStatus}
                    llmAvailable={collars.length > 0}
                    teamSynergy={teamSynergy}
                  />

                  <div className="h-px bg-border shrink-0 my-1.5" />

                  <div className="flex-1 overflow-auto min-h-0">
                    <Overview
                      roster={roster.filter((r) => r.cat.age > 1 && !r.cat.retired)}
                      collars={collars}
                      llmAvailable={collars.length > 0}
                      hideBreedTab
                    />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <div className="h-px bg-border shrink-0" />

            <StatusBar status={saveInfo.status} />
          </div>
        </div>
        )}
      </div>
    </TooltipProvider>
  );
}
