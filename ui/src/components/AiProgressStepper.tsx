import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const STEPS = [
  'Summoning the Cat Council...',
  'Inspecting collar enchantments...',
  'Judging paw formations...',
  'Weighing team synergies...',
  'Consulting the ancient yarn...',
];

const STEP_MS = 2000;
const DONE_LINGER_MS = 1200;

export function AiProgressStepper({ active }: { active: boolean }) {
  const [step, setStep] = useState(0);
  const [phase, setPhase] = useState<'idle' | 'running' | 'done'>('idle');
  const prevActive = useRef(false);

  useEffect(() => {
    if (active && !prevActive.current) {
      setStep(0);
      setPhase('running');
    } else if (!active && prevActive.current) {
      setPhase('done');
    }
    prevActive.current = active;
  }, [active]);

  useEffect(() => {
    if (phase !== 'running') return;

    const id = setInterval(() => {
      setStep((prev) => (prev < STEPS.length - 1 ? prev + 1 : prev));
    }, STEP_MS);

    return () => clearInterval(id);
  }, [phase]);

  useEffect(() => {
    if (phase !== 'done') return;
    const id = setTimeout(() => setPhase('idle'), DONE_LINGER_MS);
    return () => clearTimeout(id);
  }, [phase]);

  const visible = phase === 'running' || phase === 'done';
  const progress = phase === 'done' ? 100 : ((step + 1) / STEPS.length) * 90;
  const label = phase === 'done' ? 'Team assembled!' : STEPS[step];

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          transition={{ duration: 0.3 }}
          className="w-full mt-2 overflow-hidden"
        >
          <div className="flex items-center justify-between px-1 mb-1">
            <div className="flex items-center gap-1.5 min-w-0">
              <span className="animate-pulse-dot inline-block w-1.5 h-1.5 rounded-full bg-accent shrink-0" />
              <AnimatePresence mode="wait">
                <motion.span
                  key={label}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  transition={{ duration: 0.2 }}
                  className="text-[10px] text-text-dim font-serif italic truncate"
                >
                  {label}
                </motion.span>
              </AnimatePresence>
            </div>

            {phase === 'running' && (
              <span className="text-[9px] font-mono text-text-dim tabular-nums shrink-0 ml-2">
                {step + 1}/{STEPS.length}
              </span>
            )}
          </div>

          <div className="h-[3px] w-full rounded-full bg-border-subtle overflow-hidden">
            <motion.div
              className="h-full rounded-full bg-accent"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.5, ease: 'easeOut' }}
            />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
