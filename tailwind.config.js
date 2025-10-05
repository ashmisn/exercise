/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {},
  },
  plugins: [],
};
// tailwind.config.js

module.exports = {
  // ... other configurations (content, darkMode, etc.)
  theme: {
    extend: {
      // 1. Define the 'blob' keyframes for movement and scaling
      keyframes: {
        blob: {
          '0%, 100%': {
            transform: 'translate(0px, 0px) scale(1)',
          },
          '33%': {
            transform: 'translate(30px, -50px) scale(1.1)',
          },
          '66%': {
            transform: 'translate(-20px, 20px) scale(0.9)',
          },
        },
      },
      // 2. Define the 'animation-blob' utility
      animation: {
        'blob': 'blob 7s infinite cubic-bezier(0.4, 0, 0.6, 1)',
      },
      // 3. Define a custom shadow (if you can't use arbitrary values in CSS)
      // This is less common but necessary for the specific aesthetic
      boxShadow: {
        'inner-custom': 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.2)', // A light inner shadow
      },
    },
  },
  // ... plugins
}
