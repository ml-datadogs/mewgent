import { motion, AnimatePresence } from 'framer-motion';

interface StatusBarProps {
  status: string;
}

export function StatusBar({ status }: StatusBarProps) {
  const isLoading = status.toLowerCase().includes('waiting');
  const isLoaded = status.toLowerCase().includes('loaded');

  return (
    <div className="flex items-center justify-center gap-2 py-0.5">
      <motion.div
        className={`w-1.5 h-1.5 rounded-full ${
          isLoaded ? 'bg-good' : isLoading ? 'bg-medium' : 'bg-text-dim'
        }`}
        animate={
          isLoading
            ? { scale: [1, 0.7, 1], opacity: [1, 0.4, 1] }
            : { scale: 1, opacity: 1 }
        }
        transition={
          isLoading
            ? { duration: 1.5, repeat: Infinity, ease: 'easeInOut' }
            : { duration: 0.3 }
        }
      />
      <AnimatePresence mode="wait">
        <motion.span
          key={status}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.2 }}
          className="text-[11px] font-serif text-text-dim"
        >
          {status}
        </motion.span>
      </AnimatePresence>
    </div>
  );
}
