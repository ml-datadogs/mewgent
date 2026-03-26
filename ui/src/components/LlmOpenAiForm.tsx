import { useEffect, useState } from 'react';
import brainchipUrl from '@/assets/brainchip.png';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { applyLlmSettings, type LlmSettings } from '@/bridge';
import { getLlmAdvisorTooltip, llmAdvisorTitleAttr } from '@/lib/llmAdvisorCopy';
import { cn } from '@/lib/utils';

export interface LlmOpenAiFormProps {
  bridgeConnected: boolean;
  settings: LlmSettings | null;
  /** Carousel overlay: high-contrast light card */
  surface?: 'carousel' | 'panel';
  className?: string;
  /** After successful Apply (save key or update model) */
  onConfigured?: () => void;
}

function surfaceShell(surface: 'carousel' | 'panel', className?: string) {
  return cn(
    surface === 'carousel'
      ? 'rounded-lg border border-white/25 bg-white/92 shadow-md backdrop-blur-sm'
      : 'sketchy-frame rounded-md bg-white/25',
    className,
  );
}

export function LlmOpenAiForm({
  bridgeConnected,
  settings,
  surface = 'panel',
  className,
  onConfigured,
}: LlmOpenAiFormProps) {
  const [model, setModel] = useState('');
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (settings) setModel(settings.model);
  }, [settings]);

  if (!settings || !settings.enabled) {
    return null;
  }

  const shell = surfaceShell(surface, className);

  if (!bridgeConnected) {
    const modelOptions = settings.models.includes(model) ? settings.models : [model, ...settings.models];
    return (
      <div className={cn('flex flex-col gap-2 px-2 py-2', shell)}>
        <span className="text-[10px] font-mono font-bold text-accent tracking-wider">OPENAI</span>
        <p className="text-[10px] font-mono text-text-dim leading-snug">
          Paste your API key in the <span className="text-text font-bold">Mewgent desktop app</span> (this
          overlay). Browser dev preview has no bridge — fields below are a preview only.
        </p>
        <div className="flex flex-col gap-1.5 opacity-60 pointer-events-none">
          <label className="text-[9px] font-mono font-bold text-text-dim tracking-wider">Model</label>
          <select
            value={model}
            disabled
            className="w-full text-[11px] font-mono rounded border border-black/15 bg-white/60 px-2 py-1 text-text"
          >
            {modelOptions.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
          <label className="text-[9px] font-mono font-bold text-text-dim tracking-wider">API key</label>
          <input
            type="password"
            disabled
            placeholder="sk-... (set in desktop app)"
            className="w-full text-[11px] font-mono rounded border border-black/15 bg-white/60 px-2 py-1 text-text"
          />
        </div>
      </div>
    );
  }

  if (settings.mock) {
    return (
      <div className={cn('rounded-md px-2 py-2 space-y-1', shell)}>
        <span className="text-[10px] font-mono font-bold text-text-dim tracking-wider">
          AI: mock mode (settings.yaml)
        </span>
        <p className="text-[9px] font-mono text-text-dim leading-snug">
          Set <span className="font-bold text-text">mock: false</span> under <span className="font-bold">llm</span>{' '}
          to use a real API key below.
        </p>
      </div>
    );
  }

  const modelOptions = settings.models.includes(model) ? settings.models : [model, ...settings.models];

  const onApply = async () => {
    setBusy(true);
    setMessage(null);
    const trimmed = apiKeyInput.trim();
    const key_action = trimmed ? ('set' as const) : ('unchanged' as const);
    const res = await applyLlmSettings({
      model: model.trim() || settings.default_model,
      key_action,
      api_key: trimmed,
    });
    setBusy(false);
    if (res.ok) {
      setApiKeyInput('');
      setMessage(trimmed ? 'API key saved.' : 'Model updated.');
      onConfigured?.();
    } else {
      setMessage(res.error ?? 'Could not save settings.');
    }
  };

  const onClearKey = async () => {
    setBusy(true);
    setMessage(null);
    const res = await applyLlmSettings({
      model: model.trim() || settings.default_model,
      key_action: 'clear',
      api_key: '',
    });
    setBusy(false);
    setApiKeyInput('');
    if (res.ok) {
      setMessage('Saved key removed. Using OPENAI_API_KEY if set.');
    } else {
      setMessage(res.error ?? 'Could not clear key.');
    }
  };

  return (
    <div className={cn('flex flex-col gap-2 px-2 py-2', shell)}>
      <span className="text-[10px] font-mono font-bold text-accent tracking-wider">OPENAI</span>
      <div className="flex flex-col gap-1.5">
        <label className="text-[9px] font-mono font-bold text-text-dim tracking-wider">Model</label>
        <select
          value={model}
          onChange={(e) => setModel(e.target.value)}
          disabled={busy}
          className="w-full text-[11px] font-mono rounded border border-black/15 bg-white/60 px-2 py-1 text-text"
        >
          {modelOptions.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>
      <div className="flex flex-col gap-1.5">
        <label className="text-[9px] font-mono font-bold text-text-dim tracking-wider">API key</label>
        <input
          type="password"
          autoComplete="off"
          spellCheck={false}
          placeholder={settings.has_saved_key ? '•••••••• (saved) — paste to replace' : 'sk-...'}
          value={apiKeyInput}
          onChange={(e) => setApiKeyInput(e.target.value)}
          disabled={busy}
          className="w-full text-[11px] font-mono rounded border border-black/15 bg-white/60 px-2 py-1 text-text placeholder:text-text-dim/50"
        />
        {settings.has_saved_key && (
          <span className="text-[9px] text-text-dim font-mono">A key is stored on this machine.</span>
        )}
        {!settings.has_saved_key && (
          <span className="text-[9px] text-text-dim font-mono">
            Or set <span className="text-accent/80">OPENAI_API_KEY</span> in the environment.
          </span>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Button size="sm" onClick={() => void onApply()} disabled={busy}>
          Apply
        </Button>
        {settings.has_saved_key && (
          <Button size="sm" variant="ghost" onClick={() => void onClearKey()} disabled={busy}>
            Clear saved key
          </Button>
        )}
      </div>
      {message && <p className="text-[9px] font-mono text-text-dim">{message}</p>}
      {!settings.available && (
        <p className="text-[9px] font-mono text-amber-800/90">
          AI actions need a valid API key (saved or environment).
        </p>
      )}
    </div>
  );
}

export function LlmAiIcon({ available, className }: { available: boolean; className?: string }) {
  return (
    <span
      className={cn(
        'relative inline-flex h-8 w-8 shrink-0 items-center justify-center overflow-visible rounded-full border p-1',
        'transition-[transform,box-shadow,border-color,background-color,filter] duration-200 ease-out',
        'group-hover:scale-[1.07] group-hover:-translate-y-px group-active:scale-100',
        available
          ? [
              'border-good/55 bg-good/20 shadow-[0_0_0_1px_rgba(74,222,128,0.12)]',
              'group-hover:border-good/85 group-hover:bg-good/30',
              'group-hover:shadow-[0_0_14px_rgba(74,222,128,0.35),0_2px_8px_rgba(0,0,0,0.12)]',
            ]
          : [
              'border-dashed border-amber-800/55 bg-amber-500/[0.08]',
              'group-hover:border-amber-600/70 group-hover:bg-amber-500/15',
              'group-hover:shadow-[0_0_10px_rgba(245,158,11,0.2)]',
            ],
        className,
      )}
      aria-hidden
    >
      <img
        src={brainchipUrl}
        alt=""
        draggable={false}
        className={cn(
          // Transparent PNG pixels can let hits pass through to layers below in embedded Chromium;
          // parent span/button keeps a solid hover target.
          'pointer-events-none h-full w-full object-contain select-none transition-[opacity,filter,transform] duration-200',
          available
            ? 'opacity-100 group-hover:brightness-110 group-hover:contrast-105'
            : 'opacity-55 grayscale contrast-90 group-hover:opacity-80 group-hover:grayscale-[35%]',
        )}
      />
      <span
        className={cn(
          'pointer-events-none absolute bottom-0 right-0 z-[1] size-2 rounded-full border-2 border-black/20',
          'transition-[background-color,box-shadow,transform] duration-200',
          'group-hover:scale-110',
          available
            ? 'bg-good shadow-[0_0_8px_rgba(74,222,128,0.85)]'
            : 'bg-text-dim/55 shadow-none group-hover:bg-text-dim/70',
        )}
        aria-hidden
      />
    </span>
  );
}

export function LlmOpenAiPopoverTrigger({
  settings,
  bridgeConnected,
}: {
  settings: LlmSettings | null;
  bridgeConnected: boolean;
}) {
  const [open, setOpen] = useState(false);

  if (!settings?.enabled || !bridgeConnected || settings.mock) {
    return null;
  }

  const advisorLabel = settings.available
    ? 'AI advisor on — OpenAI settings'
    : 'AI advisor off — add API key in settings';

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <Tooltip delayDuration={400}>
        <TooltipTrigger asChild>
          <PopoverTrigger asChild>
            <button
              type="button"
              className="group rounded-full outline-none focus-visible:ring-2 focus-visible:ring-accent/50"
              title={llmAdvisorTitleAttr(settings.available)}
              aria-label={`${advisorLabel}. ${getLlmAdvisorTooltip(settings.available)}`}
              aria-expanded={open}
            >
              <LlmAiIcon available={settings.available} />
            </button>
          </PopoverTrigger>
        </TooltipTrigger>
        <TooltipContent side="bottom" align="end" className="max-w-[15rem] text-left leading-snug">
          {getLlmAdvisorTooltip(settings.available)}
        </TooltipContent>
      </Tooltip>
      <PopoverContent className="border-border p-0" align="end" sideOffset={8}>
        <LlmOpenAiForm
          bridgeConnected={bridgeConnected}
          settings={settings}
          surface="panel"
          className="border-0 shadow-none"
          onConfigured={() => setOpen(false)}
        />
      </PopoverContent>
    </Popover>
  );
}
