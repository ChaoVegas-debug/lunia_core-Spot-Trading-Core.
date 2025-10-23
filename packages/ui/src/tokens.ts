export const colors = {
  primary: {
    500: '#00FFC8',
    600: '#00e6b3',
  },
  gray: {
    800: '#1f2937',
    900: '#0E1117',
    950: '#030712',
  },
  semantic: {
    success: '#10b981',
    warning: '#f59e0b',
    error: '#ef4444',
    info: '#3b82f6',
  },
} as const;

export const typography = {
  fonts: {
    sans: 'Inter, system-ui, sans-serif',
    mono: 'Roboto Mono, monospace',
  },
  sizes: {
    xs: '0.75rem',
    sm: '0.875rem',
    base: '1rem',
    lg: '1.125rem',
    xl: '1.25rem',
    '2xl': '1.5rem',
    '3xl': '1.875rem',
  },
} as const;

export const breakpoints = {
  mobile: '320px',
  tablet: '768px',
  desktop: '1024px',
  wide: '1280px',
} as const;

export const shadows = {
  sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
  md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
  lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
  glow: '0 0 20px rgba(0,255,200,.15)',
} as const;

export const animations = {
  durations: {
    fast: '150ms',
    normal: '300ms',
    slow: '500ms',
  },
  easings: {
    ease: 'cubic-bezier(0.4,0,0.2,1)',
    bounce: 'cubic-bezier(0.68,-0.55,0.265,1.55)',
  },
} as const;
