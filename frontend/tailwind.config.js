/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        sentinel: {
          50: '#ecfeff',
          100: '#cffafe',
          200: '#a5f3fc',
          300: '#67e8f9',
          400: '#22d3ee',
          500: '#00FFD1',  // Primary cyan
          600: '#00D4FF',  // Secondary
          700: '#3B82F6',  // Accent blue
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#0f172a',  // Dark bg
        },
      },
      animation: {
        'spin-slow': 'spin 8s linear infinite',
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
        'scan-line': 'scan-line 2s ease-in-out infinite',
        'gradient-shift': 'gradient-shift 3s ease infinite',
        'float': 'float 6s ease-in-out infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'sentinel-gradient': 'linear-gradient(135deg, #00FFD1 0%, #00D4FF 50%, #3B82F6 100%)',
      },
      boxShadow: {
        'glow-cyan': '0 0 30px rgba(0, 255, 209, 0.3), 0 0 60px rgba(0, 255, 209, 0.1)',
        'glow-blue': '0 0 30px rgba(59, 130, 246, 0.3), 0 0 60px rgba(59, 130, 246, 0.1)',
        'glow-red': '0 0 30px rgba(239, 68, 68, 0.3), 0 0 60px rgba(239, 68, 68, 0.1)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
