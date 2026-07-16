import React from 'react';
import { View, Text, ActivityIndicator, StyleSheet } from 'react-native';

interface Props {
  message?: string;
}

export default function LoadingOverlay({ message = '正在生成效果图...' }: Props) {
  return (
    <View style={styles.overlay}>
      <ActivityIndicator size="large" color="#2563eb" />
      <Text style={styles.text}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  overlay: {
    ...StyleSheet.absoluteFill,
    backgroundColor: 'rgba(255,255,255,0.92)',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 100,
  },
  text: { marginTop: 16, fontSize: 16, color: '#555' },
});
