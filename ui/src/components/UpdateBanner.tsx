import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { openUrl } from '@/bridge';
import type { UpdateInfo } from '@/bridge';

interface UpdateBannerProps {
  info: UpdateInfo;
}

export function UpdateBanner({ info }: UpdateBannerProps) {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.3 }}
        className="flex items-center gap-2 rounded-md border border-good/30 bg-good/10 px-3 py-1.5 text-[11px] font-serif"
      >
        <span className="text-good font-semibold">v{info.version} available</span>
        {info.changelog && (
          <span className="text-text-dim truncate max-w-[140px]">{info.changelog}</span>
        )}
        <div className="flex-1" />
        {info.url && (
          <button
            onClick={() => openUrl(info.url)}
            className="text-good hover:text-good/80 underline underline-offset-2 cursor-pointer transition-colors shrink-0"
          >
            Download
          </button>
        )}
        <button
          onClick={() => setDismissed(true)}
          className="text-text-dim hover:text-text ml-1 cursor-pointer transition-colors shrink-0"
        >
          ✕
        </button>
      </motion.div>
    </AnimatePresence>
  );
}
