import type { Config } from 'tailwindcss';

const c = (name: string) => `rgb(var(--c-${name}) / <alpha-value>)`;

const config: Config = {
  darkMode: 'class',
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-sans)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-mono)', 'ui-monospace', 'Menlo', 'monospace'],
      },
      colors: {
        // Theme tokens (CSS variables in globals.css, light + dark).
        bg: c('bg'),
        surface: c('surface'),
        surface2: c('surface2'),
        ink: c('ink'),
        muted: c('muted'),
        border: c('border'),
        accent: { DEFAULT: c('accent'), soft: c('accent-soft'), ink: c('accent-ink') },
        good: { DEFAULT: c('good'), soft: c('good-soft') },
        warn: { DEFAULT: c('warn'), soft: c('warn-soft') },
        bad: { DEFAULT: c('bad'), soft: c('bad-soft') },
        // Back-compat aliases for earlier scaffold code.
        background: c('bg'),
        'surface-elevated': c('surface2'),
        primary: { DEFAULT: c('accent'), hover: c('accent') },
        anatomy: {
          skeletal: '#e2d9ba',
          muscular: '#a85b50',
          cardiac: '#b96760',
          sensory: '#b0c8ce',
          arterial: '#c05245',
          venous: '#527c9f',
          nervous: '#d8b565',
          respiratory: '#b98991',
          digestive: '#b8916b',
          urinary: '#b47961',
          lymphatic: '#879f7c',
          endocrine: '#c5a09a',
          reproductive: '#bda098',
          integumentary: '#ba9b7d',
          connective: '#aec3bb',
        },
      },
      borderRadius: { card: '14px' },
      boxShadow: {
        card: '0 1px 2px rgb(var(--c-ink) / 0.04), 0 4px 16px -6px rgb(var(--c-ink) / 0.08)',
        pop: '0 12px 40px -8px rgb(var(--c-ink) / 0.28)',
      },
      keyframes: {
        'fade-up': { from: { opacity: '0', transform: 'translateY(6px)' }, to: { opacity: '1', transform: 'none' } },
        'slide-in-right': { from: { transform: 'translateX(100%)' }, to: { transform: 'none' } },
        'slide-in-up': { from: { transform: 'translateY(100%)' }, to: { transform: 'none' } },
        'fade-in': { from: { opacity: '0' }, to: { opacity: '1' } },
        shimmer: { '100%': { transform: 'translateX(100%)' } },
        'pulse-dot': { '0%,100%': { opacity: '1', transform: 'scale(1)' }, '50%': { opacity: '.35', transform: 'scale(.7)' } },
      },
      animation: {
        'fade-up': 'fade-up .28s ease-out both',
        'fade-in': 'fade-in .2s ease-out both',
        'slide-in-right': 'slide-in-right .26s cubic-bezier(.2,.8,.2,1) both',
        'slide-in-up': 'slide-in-up .26s cubic-bezier(.2,.8,.2,1) both',
        'pulse-dot': 'pulse-dot 1.1s ease-in-out infinite',
      },
    },
  },
  plugins: [],
};

export default config;
