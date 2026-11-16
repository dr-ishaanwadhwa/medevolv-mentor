import { Box, BookOpen, Compass, HelpCircle, MessageCircle, type LucideIcon } from 'lucide-react';
import type { TipId } from '@/lib/tips';

export interface NavItem {
  href: string;
  label: string;
  short: string;
  icon: LucideIcon;
  /** extra path prefixes that count as this item being active */
  also?: string[];
  tab: boolean;
  tip: TipId;
}

export const NAV: NavItem[] = [
  { href: '/ask', label: 'Ask', short: 'Ask', icon: MessageCircle, also: ['/a'], tab: true, tip: 'shell.nav.ask' },
  { href: '/why', label: 'Why was I wrong?', short: 'Why', icon: HelpCircle, tab: true, tip: 'shell.nav.why' },
  { href: '/explore', label: 'Explore', short: 'Explore', icon: Compass, also: ['/c'], tab: true, tip: 'shell.nav.explore' },
  { href: '/atlas', label: '3D Atlas', short: '3D', icon: Box, tab: true, tip: 'shell.nav.atlas' },
  { href: '/how', label: 'How it works', short: 'How', icon: BookOpen, tab: false, tip: 'shell.nav.how' },
];

/** Ask is active on /ask and shared answers (/a/*); the landing at / is not a tab (PRD 4.L, L-4). */
export function isActive(item: NavItem, pathname: string) {
  return [item.href, ...(item.also ?? [])].some((p) => pathname === p || pathname.startsWith(p + '/'));
}
