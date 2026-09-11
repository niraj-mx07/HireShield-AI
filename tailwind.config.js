/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#003e1c',
        'primary-container': '#1e5631',
        secondary: '#506354',
        'secondary-container': '#d0e5d2',
        canvas: '#fcf9f8',
        surface: '#ffffff',
        'surface-2': '#f6f3f2',
        ink: '#1c1b1b',
        'ink-muted': '#414941',
        'ink-subtle': '#717970',
        'risk-low': '#1e5631',
        'risk-low-bg': '#d0e5d2',
        'risk-moderate': '#b45309',
        'risk-moderate-bg': '#fef3c7',
        'risk-high': '#ba1a1a',
        'risk-high-bg': '#ffdad6',
        'accent-recruiter': '#5521b5',
        'accent-recruiter-bg': '#edebfe',
        'accent-document': '#9d174d',
        'accent-document-bg': '#fce7f3',
        'accent-url': '#0369a1',
        'accent-url-bg': '#e0f2fe',
      },
      fontFamily: {
        serif: ['Playfair Display', 'Georgia', 'serif'],
        sans: ['Plus Jakarta Sans', 'sans-serif'],
      },
      borderRadius: {
        '2xl': '16px',
      },
      boxShadow: {
        'subtle': '0 4px 20px -2px rgba(28, 27, 27, 0.05), 0 2px 6px -1px rgba(28, 27, 27, 0.03)',
        'floating': '0 12px 32px -4px rgba(0, 62, 28, 0.08), 0 4px 12px -2px rgba(28, 27, 27, 0.04)',
      }
    },
  },
  plugins: [],
}
