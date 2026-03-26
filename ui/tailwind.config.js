/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          blue: '#1a4e8a',
          'blue-dark': '#0f3362',
          'blue-light': '#2563c4',
          orange: '#e8751a',
          'orange-light': '#f5a05a',
          green: '#2e8b57',
        },
      },
      boxShadow: {
        card: '0 4px 24px -4px rgba(0,0,0,0.10), 0 1px 4px -1px rgba(0,0,0,0.06)',
        'card-lg': '0 8px 40px -8px rgba(0,0,0,0.14), 0 2px 8px -2px rgba(0,0,0,0.08)',
      },
      keyframes: {
        'fade-in': {
          from: { opacity: '0', transform: 'translateY(10px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'fade-in': 'fade-in 0.35s ease-out',
      },
    },
  },
  plugins: [],
}
