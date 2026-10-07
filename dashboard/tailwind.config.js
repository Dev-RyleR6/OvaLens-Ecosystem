const themedPalette = name => Object.fromEntries([50,100,200,300,400,500,600,700,800,900,950].map(level => [level, `rgb(var(--${name}-${level}) / <alpha-value>)`]));
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      fontSize: { xs: ['.875rem', '1.4'], sm: ['.875rem', '1.5'] },
      colors: {
        slate: themedPalette('slate'),
        emerald: themedPalette('emerald'),
        amber: themedPalette('amber'),
        red: themedPalette('red'),
        rose: themedPalette('rose'),
        brand: 'var(--brand-ink)',
        border: "var(--border)",
        input: "var(--input)",
        ring: "var(--focus)",
        background: "var(--background)",
        foreground: "var(--foreground)",
        // Foundation University Brand Standard
        maroon: {
          50: 'var(--maroon-surface)',
          100: 'var(--maroon-surface)',
          200: 'var(--maroon-border)',
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
          foreground: "var(--foreground)",
        },
        muted: {
          DEFAULT: "#F1F5F9",
          foreground: "#64748B",
        },
        card: {
          DEFAULT: "#FFFFFF",
          foreground: "var(--foreground)",
        },
        // Agricultural biological classification colors
        agri: {
          green: "var(--success-ink)",     // Fertile / Viable Embryo
          greenBg: "#F0FDF4",
          greenBorder: "#BBF7D0",
          amber: "#D97706",     // Infertile / Penoy Salvage
          amberBg: "#FFFBEB",
          amberBorder: "#FDE68A",
          red: "#DC2626",       // Reject / critical alert
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
