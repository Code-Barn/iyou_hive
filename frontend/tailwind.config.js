/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "../templates/**/*.html"
  ],
  theme: {
    extend: {
      screens: {
        xs: '360px',
      },
      colors: {
        primary: '#FF8C00',  // Honey-Orange
        accent: '#0064AA',   // Byers Blue
      },
    },
  },
  plugins: [],
}
