import { TooltipProvider } from '@/components/ui/tooltip';
import { TitleBar } from '@/components/TitleBar';
import { TeamPanel } from '@/components/TeamPanel';
import { Overview } from '@/components/Overview';
import { StatusBar } from '@/components/StatusBar';
import { useBridge } from '@/hooks/useBridge';

export default function App() {
  const { roster, collars, team, saveInfo, llmStatus } = useBridge();

  return (
    <TooltipProvider>
      <div className="h-full w-full p-0">
        <div
          className="h-full w-full rounded-xl border border-border bg-paper flex flex-col overflow-hidden"
          style={{ boxShadow: '0 8px 32px rgba(0,0,0,0.12)' }}
        >
          <div className="flex flex-col gap-1.5 p-3 flex-1 overflow-hidden">
            <TitleBar day={saveInfo.day} catCount={saveInfo.cat_count} />

            <div className="h-px bg-border shrink-0" />

            <TeamPanel
              team={team}
              collars={collars}
              llmStatus={llmStatus}
              llmAvailable={collars.length > 0}
            />

            <div className="h-px bg-border shrink-0" />

            <div className="flex-1 overflow-auto min-h-0">
              <Overview roster={roster} collars={collars} />
            </div>

            <div className="h-px bg-border shrink-0" />

            <StatusBar status={saveInfo.status} />
          </div>
        </div>
      </div>
    </TooltipProvider>
  );
}
