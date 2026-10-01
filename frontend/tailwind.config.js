/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{html,ts}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f0fdf7",
          100: "#d7f8e8",
          200: "#b1efd5",
          300: "#79dfb8",
          400: "#42c99c",
          500: "#20ad82",
          600: "#108966",
          700: "#106e54",
          800: "#105744",
          900: "#104839",
          950: "#052b21",
        },
      },
    },
  },
  plugins: [],
};
