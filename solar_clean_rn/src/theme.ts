export const colors = {
  bg0: '#070a0f',
  bg1: '#0b1119',
  bg2: '#101821',
  bg3: '#162231',
  bg4: '#1d2c3d',
  border: 'rgba(126, 162, 195, 0.16)',
  borderStrong: 'rgba(30, 228, 255, 0.34)',
  txt1: '#edf7ff',
  txt2: '#a9bccb',
  txt3: '#6f8798',
  txtMuted: '#516b7c',
  blue: '#37a7ff',
  cyan: '#1ee4ff',
  green: '#41f19a',
  yellow: '#ffd166',
  red: '#ff4d5e',
  orange: '#ff9f43',
  blueDim: 'rgba(55, 167, 255, 0.14)',
  cyanDim: 'rgba(30, 228, 255, 0.14)',
  greenDim: 'rgba(65, 241, 154, 0.14)',
  yellowDim: 'rgba(255, 209, 102, 0.14)',
  redDim: 'rgba(255, 77, 94, 0.14)',
  overlay: 'rgba(7, 10, 15, 0.74)',
};

export const spacing = {
  xs: 6,
  sm: 10,
  md: 14,
  lg: 18,
  xl: 24,
  xxl: 32,
};

export const radius = {
  sm: 10,
  md: 14,
  lg: 18,
  xl: 24,
  round: 999,
};

export function toneFromStatus(statusColor?: string) {
  switch (statusColor) {
    case 'success':
      return colors.green;
    case 'danger':
      return colors.red;
    default:
      return colors.yellow;
  }
}
