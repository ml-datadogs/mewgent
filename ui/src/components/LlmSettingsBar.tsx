import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { applyLlmSettings, type LlmSettings } from '@/bridge';

interface LlmSettingsBarProps {
  bridgeConnected: boolean;
  settings: LlmSettings | null;
  /** Readable on the dark home carousel (opaque panel) */
  onDarkBackground?: boolean;
}

export function LlmSettingsBar({
  bridgeConnected,
  settings,
  onDarkBackground,
}: LlmSettingsBarProps) {
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

  const shellClass =
    onDarkBackground !== undefined
      ? onDarkBackground
        ? 'rounded-lg border border-white/25 bg-white/92 shadow-md backdrop-blur-sm'
        : ''
      : '';

  if (!bridgeConnected) {
    const modelOptions = settings.models.includes(model) ? settings.models : [model, ...settings.models];
    return (
      <div className={`flex flex-col gap-2 px-2 py-2 ${shellClass}`}>
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
      <div className={`sketchy-frame rounded-md px-2 py-2 bg-white/25 space-y-1 ${shellClass}`}>
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
    <div
      className={`sketchy-frame rounded-md px-2 py-2 bg-white/25 flex flex-col gap-2 ${shellClass}`}
    >
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
