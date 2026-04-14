import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: {
          900: '#070B13',
          800: '#0C1320',
          700: '#111A2A',
          600: '#162234',
        },
        accent: {
          cyan: '#1DD3F2',
          blue: '#399DFF',
          green: '#34D399',
          amber: '#F59E0B',
          red: '#FB7185',
          violet: '#A78BFA',
        },
      },
      boxShadow: {
        panel: '0 24px 80px rgba(0, 0, 0, 0.38)',
      },
      borderRadius: {
        panel: '1.5rem',
      },
      backgroundImage: {
        glow: 'radial-gradient(circle at top left, rgba(29,211,242,0.10), transparent 35%)',
      },
    },
  },
  plugins: [],
} satisfies Config;
