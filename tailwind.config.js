/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}',
    './components/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          forest: '#4A5D4E',
          primary: '#1E5631',
          mint: '#E8F0E3',
        },
        risk: {
          low: '#1E5631',
          moderate: '#F5A623',
          high: '#D64545',
        },
        neutral: {
          text: '#1A1A1A',
          muted: '#6B7280',
          border: '#E5E7EB',
          soft: '#F8FAF8',
        },
        surface: {
          DEFAULT: '#FFFFFF',
          mint: '#E8F0E3',
          gradient: '#FFFFFF',
        },
        accent: {
          pink: '#E85D8A',
          purple: '#7C6FE0',
          teal: '#2DB89A',
          orange: '#F5A623',
          blue: '#3B82F6',
        },
      },
      fontFamily: {
        display: ['"Playfair Display"', 'Georgia', 'serif'],
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'sans-serif'],
      },
      borderRadius: {
        card: '1.125rem',
        'card-lg': '1.25rem',
      },
      boxShadow: {
        card: '0 4px 18px rgba(26, 26, 26, 0.07)',
        'card-hover': '0 12px 28px rgba(30, 86, 49, 0.12)',
        float: '0 18px 42px rgba(26, 26, 26, 0.14)',
      },
      backgroundImage: {
        'mint-gradient': 'linear-gradient(135deg, #E8F0E3 0%, #FFFFFF 72%)',
      },
      maxWidth: {
        content: '72rem',
        dashboard: '90rem',
      },
      spacing: {
        18: '4.5rem',
        22: '5.5rem',
        30: '7.5rem',
      },
      screens: {
        xs: '480px',
        '3xl': '1800px',
      },
      transitionTimingFunction: {
        'out-soft': 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
    },
  },
  plugins: [],
};
