// frontend/tailwind.config.js
const paletteColor = (name) => `rgb(var(--color-${name}) / <alpha-value>)`

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
          50:  paletteColor('brand-50'),
          100: paletteColor('brand-100'),
          200: paletteColor('brand-200'),
          300: paletteColor('brand-300'),
          400: paletteColor('brand-400'),
          500: paletteColor('brand-500'),
          600: paletteColor('brand-600'),
          700: paletteColor('brand-700'),
          900: paletteColor('brand-900')
        },
        apple: {
          bg:      paletteColor('apple-bg'),
          surface: paletteColor('apple-surface'),
          gray:    paletteColor('apple-gray'),
          dark:    paletteColor('apple-dark'),
          primary: paletteColor('apple-dark'),
          mid:     paletteColor('apple-mid'),
          light:   paletteColor('apple-light'),
          divider: paletteColor('apple-divider')
        },
        gray: {
          50: paletteColor('gray-50'), 100: paletteColor('gray-100'),
          200: paletteColor('gray-200'), 300: paletteColor('gray-300'),
          400: paletteColor('gray-400'), 500: paletteColor('gray-500'),
          600: paletteColor('gray-600'), 700: paletteColor('gray-700'),
          800: paletteColor('gray-800'),
        },
        blue: {
          50: paletteColor('blue-50'), 100: paletteColor('blue-100'),
          200: paletteColor('blue-200'), 300: paletteColor('blue-300'),
          400: paletteColor('blue-400'), 500: paletteColor('blue-500'),
          600: paletteColor('blue-600'), 700: paletteColor('blue-700'),
        },
        green: {
          50: paletteColor('green-50'), 100: paletteColor('green-100'),
          200: paletteColor('green-200'), 400: paletteColor('green-400'),
          500: paletteColor('green-500'), 600: paletteColor('green-600'),
          700: paletteColor('green-700'),
        },
        red: {
          50: paletteColor('red-50'), 100: paletteColor('red-100'),
          200: paletteColor('red-200'), 300: paletteColor('red-300'),
          400: paletteColor('red-400'), 500: paletteColor('red-500'),
          600: paletteColor('red-600'), 700: paletteColor('red-700'),
        },
        amber: {
          50: paletteColor('amber-50'), 100: paletteColor('amber-100'),
          200: paletteColor('amber-200'), 400: paletteColor('amber-400'),
          500: paletteColor('amber-500'), 600: paletteColor('amber-600'),
          700: paletteColor('amber-700'), 800: paletteColor('amber-800'),
        },
        orange: {
          100: paletteColor('orange-100'),
          500: paletteColor('orange-500'),
          700: paletteColor('orange-700'),
        },
        purple: {
          100: paletteColor('purple-100'),
          200: paletteColor('purple-200'),
          700: paletteColor('purple-700'),
        },
        yellow: {
          100: paletteColor('yellow-100'),
          700: paletteColor('yellow-700'),
        },
        status: {
          todo:    paletteColor('status-todo'),
          data:    paletteColor('status-data'),
          review:  paletteColor('status-review'),
          lab:     paletteColor('status-lab'),
          impl:    paletteColor('status-impl'),
          deploy:  paletteColor('status-deploy'),
          pending: paletteColor('status-pending'),
        }
      },
      borderRadius: {
        '2xl': '18px',
        '3xl': '24px'
      },
      boxShadow: {
        'apple-sm': 'var(--shadow-apple-sm)',
        'apple':    'var(--shadow-apple)',
        'apple-lg': 'var(--shadow-apple-lg)'
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
