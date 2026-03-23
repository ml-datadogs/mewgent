import { useState, useRef, useCallback, useEffect } from 'react';
import { motion, useMotionValue, animate } from 'framer-motion';
import { UpdateCheckButton } from '@/components/UpdateCheckButton';
import { requestClose, beginDrag, updateDrag, endDrag, openUrl } from '@/bridge';

export type AppMode = 'breeding' | 'team';

interface HomeCarouselProps {
  onSelect: (mode: AppMode) => void;
  day: number;
  catCount: number;
  connected: boolean;
  /** Vite-only mock data (no embedded app) */
  uiPreview?: boolean;
}

const CARDS: { mode: AppMode; title: string; image: string }[] = [
  { mode: 'team', title: 'TEAM', image: './mainscreens/team.png' },
  { mode: 'breeding', title: 'BREEDING', image: './mainscreens/breeding.png' },
];

const DRAG_THRESHOLD = 60;
const VELOCITY_THRESHOLD = 300;

export function HomeCarousel({ onSelect, day, catCount, connected, uiPreview }: HomeCarouselProps) {
  const [activeIndex, setActiveIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const x = useMotionValue(0);
  const dragging = useRef(false);

  const onDocMouseMove = useCallback((e: MouseEvent) => {
    if (!dragging.current) return;
    updateDrag(e.screenX, e.screenY);
  }, []);

  const onDocMouseUp = useCallback(() => {
    if (!dragging.current) return;
    dragging.current = false;
    endDrag();
    document.removeEventListener('mousemove', onDocMouseMove);
    document.removeEventListener('mouseup', onDocMouseUp);
  }, [onDocMouseMove]);

  useEffect(() => {
    return () => {
      document.removeEventListener('mousemove', onDocMouseMove);
      document.removeEventListener('mouseup', onDocMouseUp);
    };
  }, [onDocMouseMove, onDocMouseUp]);

  const onDragBarMouseDown = useCallback((e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('button')) return;
    dragging.current = true;
    beginDrag(e.screenX, e.screenY);
    document.addEventListener('mousemove', onDocMouseMove);
    document.addEventListener('mouseup', onDocMouseUp);
  }, [onDocMouseMove, onDocMouseUp]);

  const handleDragEnd = (_: unknown, info: { offset: { x: number }; velocity: { x: number } }) => {
    const w = containerRef.current?.offsetWidth ?? 400;
    const { offset, velocity } = info;

    let newIndex = activeIndex;
    if (offset.x < -DRAG_THRESHOLD || velocity.x < -VELOCITY_THRESHOLD) {
      newIndex = Math.min(activeIndex + 1, CARDS.length - 1);
    } else if (offset.x > DRAG_THRESHOLD || velocity.x > VELOCITY_THRESHOLD) {
      newIndex = Math.max(activeIndex - 1, 0);
    }

    setActiveIndex(newIndex);
    animate(x, -newIndex * w, { type: 'spring', stiffness: 350, damping: 35 });
  };

  const goTo = (index: number) => {
    const w = containerRef.current?.offsetWidth ?? 400;
    setActiveIndex(index);
    animate(x, -index * w, { type: 'spring', stiffness: 350, damping: 35 });
  };

  return (
    <div ref={containerRef} className="h-full w-full overflow-hidden relative">
      <motion.div
        className="flex h-full"
        style={{ x }}
        drag="x"
        dragConstraints={{
          left: -(CARDS.length - 1) * (containerRef.current?.offsetWidth ?? 400),
          right: 0,
        }}
        dragElastic={0.15}
        onDragEnd={handleDragEnd}
      >
        {CARDS.map((card) => (
          <div
            key={card.mode}
            className="shrink-0 h-full cursor-pointer select-none relative overflow-hidden"
            style={{ width: containerRef.current?.offsetWidth ?? '100%' }}
            onClick={() => onSelect(card.mode)}
          >
            <motion.div
              className="absolute inset-0 bg-cover bg-center"
              style={{ backgroundImage: `url(${card.image})` }}
              animate={{ scale: [1, 1.03, 1] }}
              transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/50" />
            <div
              className="absolute inset-0"
              style={{ background: 'radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,0.35) 100%)' }}
            />
            <div className="absolute inset-0 flex flex-col items-center justify-end pb-8 gap-2">
              <span
                className="font-mono text-2xl font-bold tracking-[0.25em] text-white/90 drop-shadow-lg"
                style={{ textShadow: '0 2px 12px rgba(0,0,0,0.7)' }}
              >
                {card.title}
              </span>
              <motion.span
                className="flex items-center gap-1 text-[11px] font-mono text-white/50 tracking-wider mb-1"
                animate={{ opacity: [0.4, 0.8, 0.4] }}
                transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M15 3h6v6M14 10l6.1-6.1M9 21H3v-6M10 14l-6.1 6.1" />
                </svg>
                click to open
              </motion.span>
            </div>
          </div>
        ))}
      </motion.div>

      {/* Top overlay: drag area + stats + close */}
      <div
        className="absolute inset-x-0 top-0 flex items-center gap-2 px-3 py-2 cursor-grab active:cursor-grabbing select-none"
        onMouseDown={onDragBarMouseDown}
      >
        <span
          className="text-[12px] font-mono font-semibold tracking-wide"
          style={{ color: 'rgba(255,255,255,0.7)', textShadow: '0 1px 4px rgba(0,0,0,0.8)' }}
        >
          {day > 0 ? `Day ${day}` : ''}
        </span>
        {catCount > 0 && (
          <span
            className="text-[12px] font-mono"
            style={{ color: 'rgba(255,255,255,0.55)', textShadow: '0 1px 4px rgba(0,0,0,0.8)' }}
          >
            · {catCount} cats
          </span>
        )}
        {uiPreview && (
          <span
            className="text-[10px] font-mono ml-1 px-1.5 py-0.5 rounded bg-white/15"
            style={{ color: 'rgba(255,255,255,0.85)', textShadow: '0 1px 4px rgba(0,0,0,0.8)' }}
            title="Data is static mock; run Mewgent for your save"
          >
            dev preview
          </span>
        )}
        <div className="flex-1" />
        <UpdateCheckButton connected={connected} variant="overlay" className="mr-1" />
        <button
          onClick={(e) => { e.stopPropagation(); requestClose(); }}
          className="w-5 h-5 rounded-full bg-black/30 hover:bg-black/50
            flex items-center justify-center text-white/60 hover:text-white/90
            text-xs cursor-pointer transition-colors backdrop-blur-sm"
        >
          ✕
        </button>
      </div>

      {/* Left arrow */}
      {activeIndex > 0 && (
        <button
          onClick={(e) => { e.stopPropagation(); goTo(activeIndex - 1); }}
          className="absolute left-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full
            bg-black/40 hover:bg-black/60 text-white/80 hover:text-white
            flex items-center justify-center transition-colors cursor-pointer backdrop-blur-sm"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M10 3L5 8L10 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      )}

      {/* Right arrow */}
      {activeIndex < CARDS.length - 1 && (
        <button
          onClick={(e) => { e.stopPropagation(); goTo(activeIndex + 1); }}
          className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full
            bg-black/40 hover:bg-black/60 text-white/80 hover:text-white
            flex items-center justify-center transition-colors cursor-pointer backdrop-blur-sm"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M6 3L11 8L6 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      )}

      {/* Telegram author link */}
      <button
        onClick={(e) => { e.stopPropagation(); openUrl('https://t.me/mlshitcheatsheet'); }}
        className="absolute left-3 bottom-3 w-6 h-6 flex items-center justify-center
          text-[#229ED9] hover:text-[#54B9E8] transition-colors cursor-pointer"
        title="Telegram"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
          <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
        </svg>
      </button>
    </div>
  );
}
