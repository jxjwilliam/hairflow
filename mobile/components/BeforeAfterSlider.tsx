import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Image } from 'expo-image';
import { colors, radii, spacing } from '../constants/theme';

interface Props {
  beforeImage: string;
  afterImage: string;
}

export default function BeforeAfterSlider({ beforeImage, afterImage }: Props) {
  const [mode, setMode] = useState<'side-by-side' | 'single'>('single');
  const [showAfter, setShowAfter] = useState(true);

  if (mode === 'single') {
    return (
      <View style={styles.container}>
        <Image
          source={{ uri: showAfter ? afterImage : beforeImage }}
          style={styles.image}
          contentFit="contain"
        />
        <TouchableOpacity
          style={styles.toggleBtn}
          onPress={() => setShowAfter((v) => !v)}
          accessibilityRole="button"
          accessibilityLabel="切换原图/效果图"
        >
          <Text style={styles.toggleText}>
            {showAfter ? '查看原图' : '查看效果'}
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.compareBtn}
          onPress={() => setMode('side-by-side')}
          accessibilityRole="button"
          accessibilityLabel="并排对比"
        >
          <Text style={styles.compareText}>并排对比</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.sbsRow}>
        <View style={styles.sbsSide}>
          <Text style={styles.sbsLabel}>原图</Text>
          <Image
            source={{ uri: beforeImage }}
            style={styles.sbsImage}
            contentFit="contain"
          />
        </View>
        <View style={styles.sbsSide}>
          <Text style={styles.sbsLabel}>效果</Text>
          <Image
            source={{ uri: afterImage }}
            style={styles.sbsImage}
            contentFit="contain"
          />
        </View>
      </View>
      <TouchableOpacity
        style={styles.toggleBtn}
        onPress={() => setMode('single')}
        accessibilityRole="button"
        accessibilityLabel="切换单图模式"
      >
        <Text style={styles.toggleText}>单图模式</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    width: '100%',
    alignItems: 'center',
    gap: spacing.sm,
  },
  image: {
    width: '100%',
    aspectRatio: 2 / 3,
    borderRadius: radii.md,
    maxWidth: 400,
  },
  toggleBtn: {
    backgroundColor: colors.surface,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: radii.sm,
    borderWidth: 1,
    borderColor: colors.border,
  },
  toggleText: {
    color: colors.primary,
    fontSize: 13,
    fontWeight: '600',
  },
  compareBtn: {
    paddingHorizontal: 16,
    paddingVertical: 6,
  },
  compareText: {
    color: colors.textSecondary,
    fontSize: 12,
  },
  sbsRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    width: '100%',
    maxWidth: 500,
  },
  sbsSide: {
    flex: 1,
    alignItems: 'center',
    gap: 4,
  },
  sbsLabel: {
    fontSize: 12,
    color: colors.textSecondary,
    fontWeight: '600',
  },
  sbsImage: {
    width: '100%',
    aspectRatio: 2 / 3,
    borderRadius: radii.sm,
  },
});
