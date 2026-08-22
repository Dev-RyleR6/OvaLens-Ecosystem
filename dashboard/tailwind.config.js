/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      colors: {
        border: "#E2E8F0",
        input: "#E2E8F0",
        ring: "#800000",
        background: "#F8FAFC",
        foreground: "#0F172A",
        // Foundation University Brand Standard
        maroon: {
          50: '#FDF2F2',
          100: '#FDE8E8',
          200: '#FBD5D5',
          300: '#F8B4B4',
          400: '#F98080',
          500: '#E02424',
          600: '#C81E1E',
          700: '#9B1C1C',
          800: '#800000', // FU Primary Maroon
          900: '#5C0000', // FU Dark Maroon
        },
        primary: {
          DEFAULT: "#800000",
          foreground: "#FFFFFF",
          hover: "#6B0000",
        },
        secondary: {
          DEFAULT: "#F1F5F9",
          foreground: "#0F172A",
        },
        muted: {
          DEFAULT: "#F1F5F9",
          foreground: "#64748B",
        },
        card: {
          DEFAULT: "#FFFFFF",
          foreground: "#0F172A",
        },
        // Agricultural biological classification colors
        agri: {
          green: "#15803D",     // Fertile / Viable Embryo
          greenBg: "#F0FDF4",
          greenBorder: "#BBF7D0",
          amber: "#D97706",     // Infertile / Penoy Salvage
          amberBg: "#FFFBEB",
          amberBorder: "#FDE68A",
          red: "#DC2626",       // Abnormal / Dead
          redBg: "#FEF2F2",
          redBorder: "#FECACA",
        }
      },
      boxShadow: {
        xs: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
        sm: '0 1px 3px 0 rgba(0, 0, 0, 0.07), 0 1px 2px 0 rgba(0, 0, 0, 0.04)',
        md: '0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -1px rgba(0, 0, 0, 0.04)',
      }
    },
  },
  plugins: [],
}
