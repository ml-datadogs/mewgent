import { useRef, useCallback, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Badge } from '@/components/ui/badge';
import { requestClose, beginDrag, updateDrag, endDrag } from '@/bridge';

interface TitleBarProps {
  day: number;
  catCount: number;
  onBack?: () => void;
}

export function TitleBar({ day, catCount, onBack }: TitleBarProps) {
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

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('button')) return;
    dragging.current = true;
    beginDrag(e.screenX, e.screenY);
    document.addEventListener('mousemove', onDocMouseMove);
    document.addEventListener('mouseup', onDocMouseUp);
  }, [onDocMouseMove, onDocMouseUp]);

  return (
    <div
      className="flex items-center gap-2 px-1 cursor-grab active:cursor-grabbing select-none"
      onMouseDown={onMouseDown}
    >
      <div className="flex items-center gap-2">
        {onBack && (
          <motion.button
            whileHover={{ scale: 1.15, backgroundColor: 'rgba(0,0,0,0.06)' }}
            whileTap={{ scale: 0.9 }}
            onClick={onBack}
            className="w-5 h-5 rounded-full flex items-center justify-center text-text-dim hover:text-text text-sm cursor-pointer transition-colors"
          >
            &#8592;
          </motion.button>
        )}
        <div className="w-5 h-5 rounded-full bg-accent/20 flex items-center justify-center">
          <span className="text-[10px]">🐱</span>
        </div>
        <span className="text-sm font-serif font-bold text-accent tracking-wide">
          Mewgent
        </span>
      </div>

      <div className="flex-1" />

      {day > 0 && (
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ type: 'spring', stiffness: 400, damping: 25 }}
        >
          <Badge variant="dim">
            Day {day}
          </Badge>
        </motion.div>
      )}

      {catCount > 0 && (
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ type: 'spring', stiffness: 400, damping: 25, delay: 0.05 }}
        >
          <Badge>
            {catCount} cats
          </Badge>
        </motion.div>
      )}

      <motion.button
        whileHover={{ scale: 1.15, backgroundColor: 'rgba(0,0,0,0.06)' }}
        whileTap={{ scale: 0.9 }}
        onClick={requestClose}
        className="w-5 h-5 rounded-full flex items-center justify-center text-text-dim hover:text-text text-xs cursor-pointer transition-colors"
      >
        ✕
      </motion.button>
    </div>
  );
}
