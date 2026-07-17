import React from 'react';
import { View, Image, Text, StyleSheet } from 'react-native';
import { colors } from '../constants/theme';

interface Props {
  title?: string;
  subtitle?: string;
  compact?: boolean;
}

/** Brand mark for headers / empty states */
export default function AppLogo({ title = '发型试戴', subtitle, compact }: Props) {
  return (
    <View style={[styles.row, compact && styles.compact]}>
      <Image
        source={require('../assets/logo.png')}
        style={compact ? styles.markSm : styles.mark}
        accessibilityLabel="发型试戴 logo"
      />
      <View style={styles.textCol}>
        <Text style={[styles.title, compact && styles.titleSm]}>{title}</Text>
        {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  compact: { gap: 8 },
  mark: { width: 36, height: 36, borderRadius: 8 },
  markSm: { width: 28, height: 28, borderRadius: 6 },
  textCol: { justifyContent: 'center' },
  title: { fontSize: 18, fontWeight: '700', color: colors.text },
  titleSm: { fontSize: 16 },
  subtitle: { fontSize: 12, color: colors.textSecondary, marginTop: 1 },
});
