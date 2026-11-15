import { Box, BookOpen, Compass, HelpCircle, MessageCircle, type LucideIcon } from 'lucide-react';

export interface NavItem {
  href: string;
  label: string;
  short: string;
  icon: LucideIcon;
  /** extra path prefixes that count as this item being active */
  also?: string[];
  tab: boolean;
}

export const NAV: NavItem[] = [
  { href: '/', label: 'Ask', short: 'Ask', icon: MessageCircle, tab: true },
  { href: '/why', label: 'Why was I wrong?', short: 'Why', icon: HelpCircle, tab: true },
  { href: '/explore', label: 'Explore', short: 'Explore', icon: Compass, also: ['/c'], tab: true },
  { href: '/atlas', label: '3D Atlas', short: '3D', icon: Box, tab: true },
  { href: '/how', label: 'How it works', short: 'How', icon: BookOpen, tab: false },
];

export function isActive(item: NavItem, pathname: string) {
  if (item.href === '/') return pathname === '/' || pathname.startsWith('/a/');
  return [item.href, ...(item.also ?? [])].some((p) => pathname === p || pathname.startsWith(p + '/'));
}
