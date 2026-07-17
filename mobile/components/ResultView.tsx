import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Image } from 'expo-image';
import { useLayout } from '../hooks/useLayout';
import { colors, radii, THUMB_ASPECT } from '../constants/theme';

interface Props {
  imageUrl: string;
}

export default function ResultView({ imageUrl }: Props) {
  const { contentWidth, mode, height } = useLayout();

  // Keep 2:3, but cap so it fits phone/tablet/web without dominating the screen
  const maxW = Math.min(contentWidth - 32, mode === 'phone' ? contentWidth - 32 : 420);
  const maxH = height * (mode === 'phone' ? 0.52 : 0.58);
  let w = maxW;
  let h = w / THUMB_ASPECT;
  if (h > maxH) {
    h = maxH;
    w = h * THUMB_ASPECT;
  }

  return (
    <View style={styles.wrap}>
      <Image
        source={{ uri: imageUrl }}
        style={[styles.image, { width: w, height: h }]}
        contentFit="contain"
        transition={200}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 8,
  },
  image: {
    borderRadius: radii.md,
    backgroundColor: colors.bg,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
  },
});
