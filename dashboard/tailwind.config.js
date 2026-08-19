/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        fu: {
          maroon: "#800000",
          darkmaroon: "#5C0000",
          lightmaroon: "#991B1B",
          gold: "#EAB308",
          green: "#357a38",
          darkgreen: "#285e2b",
          red: "#DC2626",
          amber: "#D97706",
        },
        dark: {
          bg: "#0F172A",       // Main Slate 900
          card: "#1E293B",     // Slate 800
          cardalt: "#334155",  // Slate 700
          border: "#334155",   // Slate 700
          muted: "#94A3B8",    // Slate 400
        }
      },
      fontFamily: {
        sans: ['Inter', 'Segoe UI', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
