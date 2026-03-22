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
import {
  LlmOpenAiForm,
  LlmOpenAiPopoverTrigger,
  LlmAiIcon,
} from '@/components/LlmOpenAiForm';

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

  const [homeLlmExpanded, setHomeLlmExpanded] = useState(true);
  const homeLlmBootstrapped = useRef(false);

  useEffect(() => {
    didAutoFill.current = false;
  }, [mode]);

  useEffect(() => {
    if (!llmSettings?.enabled || homeLlmBootstrapped.current) return;
    if (!connected && !uiPreview) return;
    homeLlmBootstrapped.current = true;
    if (connected && !uiPreview && !llmSettings.mock && llmSettings.available) {
      setHomeLlmExpanded(false);
    }
  }, [llmSettings, connected, uiPreview]);

  useEffect(() => {
    if (!connected || !llmSettings?.enabled || llmSettings.mock) return;
    if (!llmSettings.available) {
      setHomeLlmExpanded(true);
    }
  }, [connected, llmSettings?.enabled, llmSettings?.available, llmSettings?.mock]);

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

  const showHomeLlmLayer = (connected || uiPreview) && !!llmSettings?.enabled;

  const showHomeCollapsedIcon =
    connected &&
    !!llmSettings &&
    llmSettings.available &&
    !llmSettings.mock &&
    !uiPreview &&
    !homeLlmExpanded;

  const showHomeCenterCard = showHomeLlmLayer && !showHomeCollapsedIcon;

  const showHomeDone =
    connected &&
    !!llmSettings?.available &&
    !uiPreview &&
    !llmSettings?.mock &&
    homeLlmExpanded;

  const llmTitleSlot =
    llmSettings?.enabled && connected && !llmSettings.mock ? (
      <LlmOpenAiPopoverTrigger settings={llmSettings} bridgeConnected={connected} />
    ) : null;

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
              {showHomeLlmLayer && (
                <>
                  {showHomeCenterCard && (
                    <div className="absolute inset-0 z-10 flex items-center justify-center px-4 pointer-events-none">
                      <div className="pointer-events-auto relative w-full max-w-sm">
                        {showHomeDone && (
                          <button
                            type="button"
                            className="absolute -right-1 -top-1 z-20 flex h-7 w-7 items-center justify-center rounded-full bg-black/35 text-white text-xs shadow-md hover:bg-black/50"
                            onClick={() => setHomeLlmExpanded(false)}
                            aria-label="Hide OpenAI settings"
                          >
                            ✕
                          </button>
                        )}
                        <LlmOpenAiForm
                          bridgeConnected={connected}
                          settings={llmSettings}
                          surface="carousel"
                          onConfigured={() => {
                            setHomeLlmExpanded(false);
                            homeLlmBootstrapped.current = true;
                          }}
                        />
                      </div>
                    </div>
                  )}
                  {showHomeCollapsedIcon && llmSettings && (
                    <div className="absolute bottom-10 left-1/2 z-10 -translate-x-1/2 pointer-events-auto">
                      <button
                        type="button"
                        className="rounded-full outline-none focus-visible:ring-2 focus-visible:ring-white/60"
                        title="OpenAI settings"
                        aria-label="OpenAI settings"
                        onClick={() => setHomeLlmExpanded(true)}
                      >
                        <LlmAiIcon available className="h-9 w-9 border-white/40 bg-black/25 text-good backdrop-blur-sm" />
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
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
                trailingSlot={llmTitleSlot}
              />

              {updateInfo && <UpdateBanner info={updateInfo} />}

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
                trailingSlot={llmTitleSlot}
              />

              {updateInfo && <UpdateBanner info={updateInfo} />}

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
