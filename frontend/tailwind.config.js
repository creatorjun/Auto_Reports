/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    screens: {
      sm:   '640px',
      md:   '768px',
      lg:   '1024px',
      xl:   '1280px',
      '2xl':'1536px',
      '3xl':'1920px',
      '4xl':'2560px'
    },
    extend: {
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', '"SF Pro Display"', '"Segoe UI"', 'sans-serif']
      },
      fontSize: {
        'ui-xs':   ['16px', { lineHeight: '1.4' }],
        'ui-sm':   ['18px', { lineHeight: '1.5' }],
        'ui-base': ['20px', { lineHeight: '1.6' }],
        'ui-md':   ['21px', { lineHeight: '1.6' }],
        'ui-lg':   ['24px', { lineHeight: '1.5' }],
        'ui-xl':   ['48px', { lineHeight: '1' }],
        'ui-2xl':  ['57px', { lineHeight: '1' }],
      },
      colors: {
        brand: {
          50:  '#f0f4ff',
          100: '#e0e9ff',
          200: '#c0d3ff',
          500: '#0071e3',
          600: '#0071e3',
          700: '#0077ed',
          900: '#003d80'
        },
        apple: {
          gray:    '#f5f5f7',
          dark:    '#1d1d1f',
          mid:     '#6e6e73',
          light:   '#86868b',
          divider: '#d2d2d7'
        },
        status: {
          todo:    '#9ca3af',
          data:    '#3b82f6',
          review:  '#f59e0b',
          lab:     '#a855f7',
          impl:    '#22c55e',
          deploy:  '#06b6d4',
          pending: '#ef4444',
        }
      },
      borderRadius: {
        '2xl': '18px',
        '3xl': '24px'
      },
      boxShadow: {
        'apple-sm': '0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.06)',
        'apple':    '0 4px 16px rgba(0,0,0,0.06), 0 1px 4px rgba(0,0,0,0.04)',
        'apple-lg': '0 12px 40px rgba(0,0,0,0.08), 0 2px 8px rgba(0,0,0,0.04)'
      },
      maxWidth: {
        content: '1600px'
      },
      spacing: {
        '18': '4.5rem'
      }
    }
  },
  plugins: []
}
