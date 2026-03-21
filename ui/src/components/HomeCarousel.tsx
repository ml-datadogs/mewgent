import { useState, useRef, useCallback, useEffect } from 'react';
import { motion, useMotionValue, animate } from 'framer-motion';
import { requestClose, beginDrag, updateDrag, endDrag } from '@/bridge';

export type AppMode = 'breeding' | 'team';

interface HomeCarouselProps {
  onSelect: (mode: AppMode) => void;
  day: number;
  catCount: number;
}

const CARDS: { mode: AppMode; title: string; image: string }[] = [
  { mode: 'team', title: 'TEAM', image: './mainscreens/team.png' },
  { mode: 'breeding', title: 'BREEDING', image: './mainscreens/breeding.png' },
];

const DRAG_THRESHOLD = 60;
const VELOCITY_THRESHOLD = 300;

export function HomeCarousel({ onSelect, day, catCount }: HomeCarouselProps) {
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
            className="shrink-0 h-full cursor-pointer select-none relative"
            style={{ width: containerRef.current?.offsetWidth ?? '100%' }}
            onClick={() => onSelect(card.mode)}
          >
            <div
              className="absolute inset-0 bg-cover bg-center"
              style={{ backgroundImage: `url(${card.image})` }}
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/50" />
            <div className="absolute inset-0 flex items-end justify-center pb-6">
              <span
                className="font-mono text-2xl font-bold tracking-[0.25em] text-white/90 drop-shadow-lg"
                style={{ textShadow: '0 2px 12px rgba(0,0,0,0.7)' }}
              >
                {card.title}
              </span>
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
          className="text-[11px] font-mono font-semibold tracking-wide"
          style={{ color: 'rgba(255,255,255,0.7)', textShadow: '0 1px 4px rgba(0,0,0,0.8)' }}
        >
          {day > 0 ? `Day ${day}` : ''}
        </span>
        {catCount > 0 && (
          <span
            className="text-[11px] font-mono"
            style={{ color: 'rgba(255,255,255,0.55)', textShadow: '0 1px 4px rgba(0,0,0,0.8)' }}
          >
            · {catCount} cats
          </span>
        )}
        <div className="flex-1" />
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
    </div>
  );
}
