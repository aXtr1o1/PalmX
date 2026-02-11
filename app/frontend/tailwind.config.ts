import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#FFFFFF",
        foreground: "#0B0B0B", // Primary Ink
        muted: "#747474",      // Secondary Text
        border: "#E6E6E6",     // Hairlines
        surface: "#F5F5F5",    // Light Fill
        charcoal: "#181818",   // Dark Sections
        primary: {
          DEFAULT: "#D22048",  // Palm Hills Accent
          foreground: "#FFFFFF",
        },
        secondary: {
          DEFAULT: "#181818",  // Charcoal
          foreground: "#FFFFFF",
        },
      },
      borderRadius: {
        lg: "0.75rem",    // 12px
        md: "0.5rem",     // 8px
        sm: "0.25rem",    // 4px
        pill: "9999px",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "sans-serif"], // Inter acting as Helvetica proxy
        serif: ["var(--font-serif)", "serif"],     // Playfair for headings if needed, or remove if strict sans
      },
      container: {
        center: true,
        padding: "2rem",
        screens: {
          "2xl": "1400px",
        },
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
export default config;
