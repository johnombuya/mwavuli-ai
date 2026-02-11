/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
      },
      colors: {
        primary: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
        },
        sidebar: {
          DEFAULT: '#1e293b',
          hover: '#334155',
        },
        surface: {
          DEFAULT: '#ffffff',
          muted: '#f8fafc',
        },
        border: {
          DEFAULT: '#e2e8f0',
          muted: '#f1f5f9',
        },
      },
    },
  },
  plugins: [],
};
