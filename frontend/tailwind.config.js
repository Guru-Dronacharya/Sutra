/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#f0fdf4",
          100: "#dcfce7",
          500: "#22c55e",
          600: "#16a34a",
          700: "#15803d",
        },
        navy: {
          800: "#0f172a",
          900: "#020617",
        },
        sutra: {
          gold: "#f59e0b",
          saffron: "#ea580c",
        }
      },
    },
  },
  plugins: [],
};
