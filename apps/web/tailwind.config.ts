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
        ink: {
          950: '#0D1117',
          900: '#111520',
          800: '#161B25',
          700: '#1E2433',
          600: '#252D3A',
          500: '#2E384A',
        },
        stone: {
          50: '#F5F2ED',
          100: '#EBE8E1',
          200: '#D4CFC7',
          300: '#B8B2A9',
          400: '#9B9589',
          500: '#7E7870',
          600: '#6B6560',
        },
        sage: {
          200: '#B8D4C8',
          300: '#9DBDAD',
          400: '#82A695',
          500: '#6B8F7A',
          600: '#5A7A68',
          700: '#4A6657',
          800: '#344D42',
        },
        amber: {
          300: '#E4C06B',
          400: '#D4A847',
          500: '#C49A3A',
          600: '#A8832F',
        },
      },
      fontFamily: {
        display: ['var(--font-fraunces)', 'Georgia', 'serif'],
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-geist-mono)', 'ui-monospace', 'monospace'],
      },
      animation: {
        'spin-slow': 'spin 1.2s linear infinite',
      },
    },
  },
  plugins: [],
};

export default config;
