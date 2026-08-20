/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['"Space Grotesk"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        obsidian: {
          950: '#070A11',
          900: '#0C101B',
          850: '#0F1523',
          800: '#121826',
          700: '#1A2234',
          600: '#253147',
          500: '#334155',
        },
        brand: {
          maroon: '#800000',
          darkMaroon: '#5C0000',
          lightMaroon: '#991B1B',
          green: '#16A34A',
          red: '#DC2626',
          amber: '#D97706',
          gold: '#EAB308',
        }
      },
      backgroundImage: {
        'tech-grid': 'radial-gradient(circle, rgba(255, 255, 255, 0.05) 1px, transparent 1px)',
      },
      backgroundSize: {
        'tech-grid': '20px 20px',
      }
    },
  },
  plugins: [],
}
