import { useState, useEffect, useRef, useCallback } from 'react';
import { motion } from 'framer-motion';
import { checkForUpdates, onUpdateCheckStatus } from '@/bridge';
import type { UpdateCheckPayload } from '@/bridge';

interface UpdateCheckButtonProps {
  connected: boolean;
  variant?: 'paper' | 'overlay';
  className?: string;
}

function messageForPayload(p: UpdateCheckPayload): string | null {
  switch (p.state) {
    case 'checking':
      return 'Checking for updates…';
    case 'disabled':
      return 'Update check URL not configured';
    case 'error':
      return p.message;
    case 'current':
      return `You're on v${p.current} (latest)`;
    case 'available':
      return `Update available: v${p.version}`;
    default:
      return null;
  }
}

export function UpdateCheckButton({
  connected,
  variant = 'paper',
  className = '',
}: UpdateCheckButtonProps) {
  const [hint, setHint] = useState<string | null>(null);
  const clearTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const scheduleClear = useCallback(() => {
    if (clearTimer.current) clearTimeout(clearTimer.current);
    clearTimer.current = setTimeout(() => setHint(null), 4500);
  }, []);

  useEffect(() => {
    if (!connected) return;
    onUpdateCheckStatus((p: UpdateCheckPayload) => {
      setHint(messageForPayload(p));
      if (p.state !== 'checking') scheduleClear();
    });
  }, [connected, scheduleClear]);

  useEffect(
    () => () => {
      if (clearTimer.current) clearTimeout(clearTimer.current);
    },
    [],
  );

  const baseBtn =
    variant === 'overlay'
      ? 'text-[10px] font-mono font-semibold tracking-wide rounded px-2 py-0.5 ' +
        'bg-black/30 hover:bg-black/50 text-white/70 hover:text-white/95 ' +
        'backdrop-blur-sm transition-colors cursor-pointer'
      : 'text-[10px] text-text-dim hover:text-text rounded px-2 py-0.5 ' +
        'hover:bg-black/[0.04] transition-colors cursor-pointer';

  return (
    <div className={`relative flex flex-col items-end gap-0.5 ${className}`}>
      <motion.button
        type="button"
        whileHover={connected ? { scale: 1.03 } : undefined}
        whileTap={connected ? { scale: 0.97 } : undefined}
        disabled={!connected}
        title={
          connected
            ? 'Check for updates (version.json)'
            : 'Available when running inside Mewgent'
        }
        onClick={(e) => {
          e.stopPropagation();
          if (!connected) return;
          checkForUpdates();
        }}
        className={`${baseBtn} ${!connected ? 'opacity-40 cursor-not-allowed hover:bg-transparent' : ''}`}
      >
        Check updates
      </motion.button>
      {hint && (
        <span
          className={
            variant === 'overlay'
              ? 'absolute top-full right-0 mt-1 max-w-[200px] text-right text-[10px] font-mono leading-tight px-2 py-1 rounded bg-black/55 text-white/85 backdrop-blur-sm pointer-events-none z-10'
              : 'absolute top-full right-0 mt-1 max-w-[200px] text-right text-[10px] leading-tight text-text-dim px-1 pointer-events-none z-10'
          }
        >
          {hint}
        </span>
      )}
    </div>
  );
}
