import * as React from 'react';
import { cn } from '@/lib/utils';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'accent' | 'dim';
}

const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = 'default', ...props }, ref) => (
    <span
      ref={ref}
      className={cn(
        'inline-flex items-center rounded-md px-1.5 py-0.5 text-[10px] font-mono font-semibold transition-colors',
        {
          'bg-bg-dim text-text border border-border': variant === 'default',
          'bg-accent/10 text-accent border border-accent/20': variant === 'accent',
          'bg-transparent text-text-dim': variant === 'dim',
        },
        className,
      )}
      {...props}
    />
  ),
);
Badge.displayName = 'Badge';

export { Badge };
