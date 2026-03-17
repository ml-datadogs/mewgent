import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-1.5 rounded-md text-sm font-medium transition-all duration-150 cursor-pointer disabled:pointer-events-none disabled:opacity-50 active:scale-[0.97]',
  {
    variants: {
      variant: {
        default: 'bg-bg-dim border border-border text-text hover:bg-black/[0.07]',
        primary: 'bg-good text-white hover:bg-good/90 border border-good/30',
        destructive: 'bg-transparent border border-border text-text-dim hover:text-accent hover:border-accent/50',
        ghost: 'bg-transparent text-text-dim hover:text-text hover:bg-black/[0.04]',
      },
      size: {
        default: 'h-7 px-3 text-xs',
        sm: 'h-6 px-2 text-[11px]',
        icon: 'h-5 w-5 text-xs',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
);

interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  ),
);
Button.displayName = 'Button';

export { Button, buttonVariants };
