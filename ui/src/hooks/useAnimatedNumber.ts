import { useEffect, useRef, useState } from 'react';
import { animate } from 'framer-motion';

export function useAnimatedNumber(value: number, duration = 0.6): string {
  const [display, setDisplay] = useState(value.toFixed(1));
  const prevRef = useRef(value);

  useEffect(() => {
    if (prevRef.current !== value) {
      const from = prevRef.current;
      prevRef.current = value;
      const controls = animate(from, value, {
        duration,
        ease: 'easeOut',
        onUpdate: (v) => setDisplay(v.toFixed(1)),
      });
      return () => controls.stop();
    }
  }, [value, duration]);

  return display;
}
