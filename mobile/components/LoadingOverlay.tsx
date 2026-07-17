import React from 'react';
import { View, Text, ActivityIndicator, StyleSheet } from 'react-native';
import { colors } from '../constants/theme';

interface Props {
  message?: string;
}

export default function LoadingOverlay({ message = '正在生成效果图…' }: Props) {
  return (
    <View style={styles.overlay}>
      <ActivityIndicator size="large" color={colors.primary} />
      <Text style={styles.text}>{message}</Text>
      <Text style={styles.hint}>通常需要 30–60 秒，请稍候</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  overlay: {
    ...StyleSheet.absoluteFill,
    backgroundColor: 'rgba(255,255,255,0.94)',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 100,
  },
  text: { marginTop: 16, fontSize: 16, color: colors.text, fontWeight: '600' },
  hint: { marginTop: 8, fontSize: 13, color: colors.textMuted },
});
