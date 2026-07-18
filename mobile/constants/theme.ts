/** Shared visual tokens for web / phone / tablet */

export const colors = {
  bg: '#f4f5f7',
  surface: '#ffffff',
  text: '#1a1a1a',
  textSecondary: '#6b7280',
  textMuted: '#9ca3af',
  border: '#e5e7eb',
  primary: '#1d4ed8',
  primarySoft: '#eff6ff',
  success: '#047857',
  danger: '#b91c1c',
  overlay: 'rgba(0,0,0,0.45)',
  // Membership tier colors
  tierFree: '#6b7280',
  tierFreeBg: '#f3f4f6',
  tierPro: '#2563eb',
  tierProBg: '#eff6ff',
  tierPremium: '#d97706',
  tierPremiumBg: '#fffbeb',
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
};

export const radii = {
  sm: 8,
  md: 12,
  lg: 16,
  pill: 999,
};

/** Catalog PNGs are 512×768 */
export const THUMB_ASPECT = 2 / 3;

/** Max content width on large web / tablet landscape */
export const CONTENT_MAX_WIDTH = 1080;

export const breakpoints = {
  phone: 0,
  tablet: 600,
  desktop: 900,
} as const;
