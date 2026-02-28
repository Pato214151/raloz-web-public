/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        raloz: {
          50: '#f0f4ff',
          100: '#dce4ff',
          200: '#bfcdff',
          300: '#93abff',
          400: '#607eff',
          500: '#3b52ff',
          600: '#1e2ff5',
          700: '#1a24e1',
          800: '#1b20b6',
          900: '#1c218f',
          950: '#141557',
        },
        success: '#22c55e',
        warning: '#f59e0b',
        danger: '#ef4444',
      }
    },
  },
  plugins: [],
}
