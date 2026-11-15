'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { BookOpen } from 'lucide-react';
import { cn } from '@/lib/cn';
import { Toaster } from '@/components/ui';
import { NAV, isActive } from './nav';
import { Wordmark } from './Logo';
import { ThemeToggle } from './ThemeToggle';

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() ?? '/';
  return (
    <div className="min-h-dvh md:pl-[var(--rail-w)]">
      <a
        href="#main"
        className="sr-only z-[70] rounded-lg bg-accent px-3 py-2 text-accent-ink focus:not-sr-only focus:fixed focus:left-3 focus:top-3"
      >
        Skip to content
      </a>

      {/* Desktop rail */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[var(--rail-w)] flex-col border-r border-border bg-surface/60 px-3 py-5 backdrop-blur md:flex">
        <Link href="/" className="mb-6 rounded-xl px-2 py-1" aria-label="MedEvolv Mentor home">
          <Wordmark />
        </Link>
        <nav aria-label="Main" className="flex flex-col gap-1">
          {NAV.map((item) => {
            const active = isActive(item, pathname);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? 'page' : undefined}
                className={cn(
                  'flex min-h-[40px] items-center gap-3 rounded-xl px-3 text-[0.93rem] font-medium transition-colors',
                  active ? 'bg-accent-soft text-accent' : 'text-muted hover:bg-surface2 hover:text-ink',
                )}
              >
                <Icon className="h-[18px] w-[18px]" aria-hidden />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="mt-auto space-y-3 px-1">
          <p className="text-xs leading-relaxed text-muted">
            A study aid, not medical advice. Answers come only from the indexed textbooks.
          </p>
          <div className="flex items-center justify-between">
            <span className="label-mono">Theme</span>
            <ThemeToggle />
          </div>
        </div>
      </aside>

      {/* Mobile top bar */}
      <header className="sticky top-0 z-30 flex h-[var(--topbar-h)] items-center justify-between border-b border-border bg-bg/85 px-3 backdrop-blur md:hidden">
        <Link href="/" aria-label="MedEvolv Mentor home" className="rounded-lg">
          <Wordmark />
        </Link>
        <div className="flex items-center">
          <Link
            href="/how"
            aria-label="How it works"
            className="grid h-11 w-11 place-items-center rounded-xl text-muted hover:bg-surface2 hover:text-ink"
          >
            <BookOpen className="h-[18px] w-[18px]" />
          </Link>
          <ThemeToggle />
        </div>
      </header>

      <main id="main" className="pb-tabbar min-h-[calc(100dvh-var(--topbar-h))] md:min-h-dvh">
        {children}
      </main>

      {/* Mobile bottom tab bar */}
      <nav
        aria-label="Main"
        className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-4 border-t border-border bg-surface/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden"
      >
        {NAV.filter((n) => n.tab).map((item) => {
          const active = isActive(item, pathname);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? 'page' : undefined}
              className={cn(
                'flex h-[var(--tabbar-h)] flex-col items-center justify-center gap-0.5 text-[0.7rem] font-medium',
                active ? 'text-accent' : 'text-muted',
              )}
            >
              <Icon className={cn('h-5 w-5', active && 'stroke-[2.4]')} aria-hidden />
              {item.short}
            </Link>
          );
        })}
      </nav>

      <Toaster />
    </div>
  );
}
