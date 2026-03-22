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

const RADIUS = 68;
const STROKE = 6;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
const SIZE = (RADIUS + STROKE) * 2;

export function AiCircleProgress({ active }: { active: boolean }) {
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
  const progress = phase === 'done' ? 1 : ((step + 1) / STEPS.length) * 0.9;
  const dashOffset = CIRCUMFERENCE * (1 - progress);
  const label = phase === 'done' ? 'Team assembled!' : STEPS[step];

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, scale: 0.85 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.9 }}
          transition={{ duration: 0.35, ease: 'easeOut' }}
          className="flex flex-col items-center justify-center"
        >
          <div className="relative" style={{ width: SIZE, height: SIZE }}>
            <svg
              width={SIZE}
              height={SIZE}
              viewBox={`0 0 ${SIZE} ${SIZE}`}
              className="block"
            >
              <circle
                cx={SIZE / 2}
                cy={SIZE / 2}
                r={RADIUS}
                fill="none"
                stroke="var(--color-border)"
                strokeWidth={STROKE}
                strokeOpacity={0.3}
              />
              <motion.circle
                cx={SIZE / 2}
                cy={SIZE / 2}
                r={RADIUS}
                fill="none"
                stroke="var(--color-accent)"
                strokeWidth={STROKE}
                strokeLinecap="round"
                strokeDasharray={CIRCUMFERENCE}
                initial={{ strokeDashoffset: CIRCUMFERENCE }}
                animate={{ strokeDashoffset: dashOffset }}
                transition={{ duration: 0.6, ease: 'easeOut' }}
                transform={`rotate(-90 ${SIZE / 2} ${SIZE / 2})`}
              />
            </svg>

            <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
              <div className="m-auto flex size-fit max-w-[min(100%,11rem)] flex-col items-center gap-1 px-3 text-center">
                <AnimatePresence mode="wait">
                  <motion.span
                    key={label}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -4 }}
                    transition={{ duration: 0.2 }}
                    className="text-[11px] text-text italic leading-tight"
                  >
                    {label}
                  </motion.span>
                </AnimatePresence>

                {phase === 'running' && (
                  <span className="text-[10px] font-mono text-text-dim tabular-nums">
                    {step + 1}/{STEPS.length}
                  </span>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
