/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        // Hynex-inspired deep charcoal & neon palette
        bento: {
          bg: "#0B0D13",
          card: "#121620",
          cardHover: "#161B27",
          subtle: "#1B202D",
          border: "#1F2636",
          borderLight: "rgba(255, 255, 255, 0.08)",
          textMuted: "#8E98A8",
        },
        maroon: {
          DEFAULT: "#800000",
          glow: "rgba(128, 0, 0, 0.35)",
          dark: "#5C0000",
          light: "#991B1B",
        },
        neon: {
          green: "#10B981",
          greenGlow: "rgba(16, 185, 129, 0.3)",
          cyan: "#06B6D4",
          cyanGlow: "rgba(6, 182, 212, 0.3)",
          amber: "#F59E0B",
          amberGlow: "rgba(245, 158, 11, 0.3)",
          rose: "#EF4444",
        }
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
      boxShadow: {
        'bento': '0 8px 30px rgba(0, 0, 0, 0.45)',
        'glow-cyan': '0 0 25px rgba(6, 182, 212, 0.25)',
        'glow-green': '0 0 25px rgba(16, 185, 129, 0.25)',
        'glow-maroon': '0 0 25px rgba(128, 0, 0, 0.35)',
        'glow-amber': '0 0 25px rgba(245, 158, 11, 0.25)',
      }
    },
  },
  plugins: [],
}
