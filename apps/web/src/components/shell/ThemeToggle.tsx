'use client';

import { useEffect, useState } from 'react';
import { Moon, Sun } from 'lucide-react';
import { cn } from '@/lib/cn';
import { Tooltip } from '@/components/ui/Tooltip';

export function ThemeToggle({ className }: { className?: string }) {
  const [dark, setDark] = useState<boolean | null>(null);
  useEffect(() => setDark(document.documentElement.classList.contains('dark')), []);

  const toggle = () => {
    const next = !document.documentElement.classList.contains('dark');
    document.documentElement.classList.toggle('dark', next);
    document.documentElement.style.colorScheme = next ? 'dark' : 'light';
    try {
      localStorage.setItem('mm-theme', next ? 'dark' : 'light');
    } catch {
      /* storage unavailable: theme still applies for this visit */
    }
    setDark(next);
  };

  return (
    <Tooltip tip={dark ? 'shell.theme.toLight' : 'shell.theme.toDark'} iconOnly>
    <button
      type="button"
      onClick={toggle}
      aria-label={dark ? 'Switch to light theme' : 'Switch to dark theme'}
      className={cn('grid h-11 w-11 place-items-center rounded-xl text-muted hover:bg-surface2 hover:text-ink md:h-9 md:w-9', className)}
    >
      {dark === null ? <span className="h-[18px] w-[18px]" /> : dark ? <Sun className="h-[18px] w-[18px]" /> : <Moon className="h-[18px] w-[18px]" />}
    </button>
    </Tooltip>
  );
}
