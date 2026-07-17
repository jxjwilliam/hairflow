import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Image } from 'expo-image';
import { colors, radii, spacing } from '../constants/theme';

export type AngleKey = 'front' | 'left' | 'right' | 'back';

interface AngleData {
  key: AngleKey;
  label: string;
  url: string;
}

interface Props {
  angles: AngleData[];
  activeAngle: AngleKey;
  onAngleChange: (angle: AngleKey) => void;
}

const ANGLE_LABELS: Record<AngleKey, string> = {
  front: '正面',
  left: '左侧',
  right: '右侧',
  back: '后侧',
};

export default function AngleSelector({ angles, activeAngle, onAngleChange }: Props) {
  return (
    <View style={styles.container}>
      {angles.map((angle) => {
        const isActive = angle.key === activeAngle;
        return (
          <TouchableOpacity
            key={angle.key}
            style={[styles.thumb, isActive && styles.thumbActive]}
            onPress={() => onAngleChange(angle.key)}
            accessibilityRole="button"
            accessibilityLabel={`${ANGLE_LABELS[angle.key]}视图`}
          >
            <Image
              source={{ uri: angle.url }}
              style={styles.thumbImage}
              contentFit="cover"
            />
            <Text style={[styles.label, isActive && styles.labelActive]}>
              {ANGLE_LABELS[angle.key]}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: spacing.sm,
    paddingVertical: spacing.sm,
  },
  thumb: {
    width: 64,
    height: 64,
    borderRadius: radii.sm,
    overflow: 'hidden',
    borderWidth: 2,
    borderColor: 'transparent',
    alignItems: 'center',
  },
  thumbActive: {
    borderColor: colors.primary,
  },
  thumbImage: {
    width: 60,
    height: 48,
    borderRadius: 4,
  },
  label: {
    fontSize: 10,
    color: colors.textSecondary,
    marginTop: 2,
  },
  labelActive: {
    color: colors.primary,
    fontWeight: '600',
  },
});
