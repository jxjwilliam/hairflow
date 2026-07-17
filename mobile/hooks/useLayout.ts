import { useMemo } from 'react';
import { useWindowDimensions } from 'react-native';
import { breakpoints, CONTENT_MAX_WIDTH } from '../constants/theme';

export type LayoutMode = 'phone' | 'tablet' | 'desktop';

export function useLayout() {
  const { width, height } = useWindowDimensions();

  return useMemo(() => {
    const mode: LayoutMode =
      width >= breakpoints.desktop
        ? 'desktop'
        : width >= breakpoints.tablet
          ? 'tablet'
          : 'phone';

    const columns = mode === 'desktop' ? 4 : mode === 'tablet' ? 3 : 2;
    const contentWidth = Math.min(width, CONTENT_MAX_WIDTH);
    const horizontalPad = mode === 'phone' ? 12 : 20;
    const gutter = mode === 'phone' ? 8 : 12;
    const cardWidth = (contentWidth - horizontalPad * 2 - gutter * (columns - 1)) / columns;

    return {
      width,
      height,
      mode,
      columns,
      contentWidth,
      horizontalPad,
      gutter,
      cardWidth,
      isWide: mode !== 'phone',
    };
  }, [width, height]);
}
