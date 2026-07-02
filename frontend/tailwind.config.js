/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          50: "#f6f7f9",
          100: "#eceef2",
          200: "#d3d9e2",
          300: "#a9b3c4",
          400: "#7885a0",
          500: "#586582",
          600: "#3f4a63",
          700: "#2b3448",
          800: "#1b2233",
          900: "#0f1524",
        },
        brand: {
          50: "#e6f5ef",
          100: "#cce9de",
          200: "#99d3bd",
          300: "#5bb598",
          400: "#2d9977",
          500: "#0e7d5e",
          600: "#046046",
          700: "#014835",
          800: "#013a2b",
          900: "#012a1f",
        },
        signal: {
          good: "#10b981",
          warn: "#f59e0b",
          bad: "#ef4444",
        },
      },
      fontFamily: {
        sans: [
          "InterVariable",
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        display: [
          "InterVariable",
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "sans-serif",
        ],
      },
      boxShadow: {
        card: "0 1px 2px rgba(15,21,36,0.04), 0 4px 24px -8px rgba(15,21,36,0.08)",
        pop: "0 8px 40px -12px rgba(15,21,36,0.20)",
      },
    },
  },
  plugins: [],
};
