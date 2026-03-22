import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { TooltipProvider } from '@/components/ui/tooltip';
import { TitleBar } from '@/components/TitleBar';
import { HomeCarousel, type AppMode } from '@/components/HomeCarousel';
import { TeamPanel } from '@/components/TeamPanel';
import { BreedingPanel } from '@/components/BreedingPanel';
import { StatusBar } from '@/components/StatusBar';
import { UpdateBanner } from '@/components/UpdateBanner';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useBridge } from '@/hooks/useBridge';
import { autofillTeamLlm } from '@/bridge';
import { LlmSettingsBar } from '@/components/LlmSettingsBar';

const pageVariants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -16 },
};

export default function App() {
  const { connected, uiPreview, roster, collars, team, teamSynergy, saveInfo, llmStatus, updateInfo, roomStats, llmSettings } =
    useBridge();
  const showAiControls =
    uiPreview || (connected && llmSettings !== null && llmSettings.available);
  const [mode, setMode] = useState<'home' | AppMode>('home');
  const cats = roster.map((r) => r.cat);
  const didAutoFill = useRef(false);

  useEffect(() => { didAutoFill.current = false; }, [mode]);

  useEffect(() => {
    if (mode !== 'team' || didAutoFill.current) return;
    if (!connected || !llmSettings?.available) return;
    const isEmpty = team.every((s) => s === null);
    if (isEmpty) {
      didAutoFill.current = true;
      autofillTeamLlm();
    }
  }, [mode, connected, team, llmSettings?.available]);

  const goHome = () => setMode('home');

  return (
    <TooltipProvider>
      <div className="h-full w-full p-0">
        {mode === 'home' && (
          <div className="h-full w-full flex flex-col overflow-hidden">
            <div className="flex-1 min-h-0 relative">
              <HomeCarousel
                onSelect={setMode}
                day={saveInfo.day}
                catCount={saveInfo.cat_count}
                connected={connected}
                uiPreview={uiPreview}
              />
            </div>
            {(connected || uiPreview) && llmSettings?.enabled && (
              <div className="shrink-0 max-h-[min(260px,45vh)] overflow-y-auto border-t border-white/10 bg-gradient-to-t from-black/55 via-black/35 to-transparent px-2 pb-2 pt-1.5">
                <LlmSettingsBar
                  bridgeConnected={connected}
                  settings={llmSettings}
                  onDarkBackground
                />
              </div>
            )}
          </div>
        )}

        {mode === 'breeding' && (
          <div className="h-full w-full flex flex-col overflow-hidden bg-paper rounded-xl">
            <div className="flex flex-col gap-1.5 p-3 flex-1 overflow-hidden">
              <TitleBar
                day={saveInfo.day}
                catCount={saveInfo.cat_count}
                connected={connected}
                onBack={goHome}
                borderless
              />

              {updateInfo && <UpdateBanner info={updateInfo} />}

              <LlmSettingsBar bridgeConnected={connected} settings={llmSettings} />

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
                  {cats.length >= 2 ? (
                    <BreedingPanel
                      cats={cats}
                      roomStats={roomStats}
                      llmAvailable={showAiControls}
                      bridgeConnected={connected}
                    />
                  ) : (
                    <div className="parchment-empty rounded-lg flex items-center justify-center h-[200px]">
                      <span className="text-[11px] font-mono font-bold text-text-dim tracking-wider opacity-50">
                        Need at least 2 cats to analyze breeding
                      </span>
                    </div>
                  )}
                </ScrollArea>
              </motion.div>

              <StatusBar status={saveInfo.status} />
            </div>
          </div>
        )}

        {mode === 'team' && (
          <div className="h-full w-full flex flex-col overflow-hidden bg-paper rounded-xl">
            <div className="flex flex-col gap-1.5 p-3 flex-1 overflow-hidden">
              <TitleBar
                day={saveInfo.day}
                catCount={saveInfo.cat_count}
                connected={connected}
                onBack={goHome}
                borderless
              />

              {updateInfo && <UpdateBanner info={updateInfo} />}

              <LlmSettingsBar bridgeConnected={connected} settings={llmSettings} />

              <motion.div
                key="team"
                variants={pageVariants}
                initial="initial"
                animate="animate"
                exit="exit"
                transition={{ duration: 0.25 }}
                className="flex-1 min-h-0 overflow-auto"
              >
                <ScrollArea className="h-full">
                  <TeamPanel
                    team={team}
                    collars={collars}
                    llmStatus={llmStatus}
                    llmAvailable={showAiControls}
                    bridgeConnected={connected}
                    teamSynergy={teamSynergy}
                  />
                </ScrollArea>
              </motion.div>

              <StatusBar status={saveInfo.status} />
            </div>
          </div>
        )}
      </div>
    </TooltipProvider>
  );
}
