import React from 'react';
import { View, StyleSheet, type ViewProps } from 'react-native';
import { usePathname } from 'expo-router';

type TabId = 'index' | 'history';

interface Props extends ViewProps {
  /** Which tab this screen belongs to — used to detect focus without react-navigation. */
  tab: TabId;
}

function isTabFocused(pathname: string, tab: TabId): boolean {
  const path = pathname.replace(/\/+$/, '') || '/';
  if (tab === 'history') {
    return path === '/history' || path.endsWith('/history');
  }
  // Catalog tab: home routes only (not /history, /capture, etc.)
  return path === '/' || path === '/index' || path.endsWith('/(tabs)') || path.endsWith('/(tabs)/index');
}

/**
 * On web, Expo tabs keep inactive scenes mounted and they can intercept clicks.
 * Hide unfocused screens completely so only the active tab receives input.
 */
export default function FocusedScreen({ tab, style, children, ...rest }: Props) {
  const pathname = usePathname();
  const focused = isTabFocused(pathname, tab);

  if (!focused) {
    return null;
  }

  return (
    <View {...rest} style={[styles.root, style]}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
});
