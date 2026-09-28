/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{html,ts}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4ff",
          100: "#d9e6ff",
          200: "#b8d0ff",
          300: "#8bb1ff",
          400: "#5a8bff",
          500: "#3366ff",
          600: "#1f4de6",
          700: "#1a3ebf",
          800: "#1a3699",
          900: "#1a307a",
          950: "#111c47",
        },
      },
    },
  },
  plugins: [],
};
