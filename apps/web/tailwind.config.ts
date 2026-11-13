import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: '#090d16',
        surface: '#0f172a',
        'surface-elevated': '#1e293b',
        border: '#334155',
        primary: {
          DEFAULT: '#0ea5e9',
          hover: '#0284c7',
        },
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
    },
  },
  plugins: [],
};

export default config;
