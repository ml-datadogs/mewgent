import type { CSSProperties } from 'react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import type { TeamStashTip } from '@/bridge';
import { cn } from '@/lib/utils';

const frameBg = 'rgba(255,255,255,0.45)';

export function StashTipWithTooltip({
  tip,
  size = 'md',
  forCatName,
  hint,
  frameClassName,
  frameStyle,
}: {
  tip: TeamStashTip;
  size?: 'sm' | 'md' | 'lg';
  /** Roster name when this tip is shown on that cat's card */
  forCatName?: string;
  /** Extra line under "Why this pick" (e.g. flex / open picks) */
  hint?: string;
  frameClassName?: string;
  frameStyle?: CSSProperties;
}) {
  const imgClass =
    size === 'sm' ? 'w-6 h-6' : size === 'lg' ? 'w-8 h-8' : 'w-7 h-7';
  const pad = size === 'sm' ? 'p-0.5' : 'p-0.5';

  return (
    <Tooltip delayDuration={250}>
      <TooltipTrigger asChild>
        <button
          type="button"
          className={cn(
            'sketchy-frame rounded-sm shrink-0 cursor-help border-0 p-0',
            'focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/50',
            pad,
            frameClassName,
          )}
          style={{ background: frameBg, ...frameStyle }}
          aria-label={`${tip.item_id}: ${tip.reason || 'stash suggestion'}`}
        >
          {tip.icon_url ? (
            <img
              src={tip.icon_url}
              alt=""
              className={cn(imgClass, 'object-contain block')}
              loading="lazy"
            />
          ) : (
            <span className="text-[8px] font-mono font-bold text-text px-1 max-w-[2.5rem] truncate block">
              {tip.item_id}
            </span>
          )}
        </button>
      </TooltipTrigger>
      <TooltipContent side="top" className="max-w-[280px] space-y-1.5 px-3 py-2.5">
        <div>
          <p className="font-mono text-[11px] font-bold text-text leading-tight">{tip.item_id}</p>
          {tip.slot ? (
            <p className="text-[10px] text-text-dim font-mono mt-0.5">{tip.slot}</p>
          ) : null}
        </div>
        {forCatName ? (
          <p className="text-[10px] text-text-dim leading-snug">
            Shown on <span className="font-semibold text-text">{forCatName}</span>
          </p>
        ) : null}
        <div className="border-t border-border-subtle pt-1.5">
          <p className="text-[9px] font-mono font-bold text-text-dim tracking-wider mb-1">
            Why this pick
          </p>
          {hint ? (
            <p className="text-[10px] text-text-dim leading-snug mb-1.5">{hint}</p>
          ) : null}
          <p className="text-xs text-text leading-snug">
            {tip.reason.trim() || 'No explanation returned from the advisor.'}
          </p>
        </div>
        {tip.effect ? (
          <p className="text-[10px] text-text-dim italic leading-snug border-t border-border-subtle pt-1.5">
            {tip.effect}
          </p>
        ) : null}
      </TooltipContent>
    </Tooltip>
  );
}
