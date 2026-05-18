/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // CAERN dark GIS palette
        bg: {
          base: "#0a0f1e",      // page background (deep navy)
          panel: "#0d1527",     // sidebars / right panel
          card: "#111827",      // card surfaces
          elev: "#162236",      // elevated card / hover
        },
        border: {
          DEFAULT: "#1e3a5f",
          subtle: "#1a2a44",
        },
        accent: {
          DEFAULT: "#00d4ff",   // electric blue
          dim: "#0099bb",
          green: "#00ff88",
          amber: "#ffaa00",
          red: "#ff4d6d",
        },
        text: {
          primary: "#e7eef9",
          muted: "#8fa1bd",
          subtle: "#5b6c87",
        },
        // Tailwind primary kept for compatibility with old code
        primary: {
          50:  "#eff6ff",
          500: "#00d4ff",
          600: "#0099bb",
          700: "#007a99",
          900: "#0d1527",
        },
        // Category-specific (matches map layers)
        cat: {
          yeni: "#00ff88",
          yikim: "#ff4d6d",
          veje: "#ffaa00",
          yuzey: "#7aa6d6",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "Menlo", "monospace"],
      },
      borderRadius: {
        sm: "6px",
        DEFAULT: "8px",
        md: "10px",
        lg: "12px",
        xl: "16px",
      },
      boxShadow: {
        glow: "0 0 20px rgba(0, 212, 255, 0.15)",
        card: "0 1px 3px rgba(0,0,0,0.4), 0 0 0 1px rgba(30,58,95,0.6)",
      },
      backgroundImage: {
        "grid-pattern":
          "linear-gradient(rgba(30,58,95,0.18) 1px, transparent 1px), linear-gradient(90deg, rgba(30,58,95,0.18) 1px, transparent 1px)",
      },
    },
  },
  plugins: [],
};
