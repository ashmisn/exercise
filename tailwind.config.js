/** @type {import('tailwindcss').Config} */
export default {
  // --- EXISTING VITE SETUP ---
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  
  theme: {
    // --- CUSTOM EXTENSIONS ARE MERGED HERE ---
    extend: {
      // 1. Define the 'blob' keyframes
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
      // 3. Define the custom shadow utility
      boxShadow: {
        // This shadow definition corresponds to the 'shadow-inner-custom' class
        'inner-custom': 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.1), inset 0 0 10px rgba(255, 255, 255, 0.15)',
      },
    },
  },
  
  // --- EXISTING VITE SETUP ---
  plugins: [],
};
