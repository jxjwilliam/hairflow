import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import Slider from '@react-native-community/slider';
import { colors, spacing, radii } from '../constants/theme';

export interface Params {
  length: number;
  curl: number;
  color: string;
}

const COLORS = [
  { name: 'black', label: '黑色', color: '#1a1a1a' },
  { name: 'brown', label: '棕色', color: '#8B4513' },
  { name: 'red', label: '红色', color: '#DC143C' },
  { name: 'blue', label: '蓝色', color: '#1E90FF' },
  { name: 'purple', label: '紫色', color: '#9370DB' },
  { name: 'blonde', label: '金色', color: '#DAA520' },
  { name: 'gray', label: '灰色', color: '#A9A9A9' },
  { name: 'pink', label: '粉色', color: '#FF69B4' },
];

interface Props {
  onRegenerate: (params: Params) => void;
  loading: boolean;
  defaultParams?: Partial<Params>;
}

export default function ParamPanel({ onRegenerate, loading, defaultParams }: Props) {
  const [length, setLength] = useState(defaultParams?.length ?? 0.5);
  const [curl, setCurl] = useState(defaultParams?.curl ?? 0.0);
  const [color, setColor] = useState(defaultParams?.color ?? 'black');

  const lengthLabel = length < 0.3 ? '短' : length < 0.6 ? '中等' : '长';
  const curlLabel = curl < 0.2 ? '直发' : curl < 0.6 ? '微卷' : '卷发';

  return (
    <View style={styles.container}>
      <Text style={styles.sectionTitle}>发型参数调整</Text>

      <View style={styles.sliderRow}>
        <Text style={styles.sliderLabel}>发长: {lengthLabel}</Text>
        <Slider
          style={styles.slider}
          minimumValue={0}
          maximumValue={1}
          step={0.1}
          value={length}
          onValueChange={setLength}
          minimumTrackTintColor={colors.primary}
          maximumTrackTintColor={colors.border}
          thumbTintColor={colors.primary}
        />
      </View>

      <View style={styles.sliderRow}>
        <Text style={styles.sliderLabel}>卷曲: {curlLabel}</Text>
        <Slider
          style={styles.slider}
          minimumValue={0}
          maximumValue={1}
          step={0.1}
          value={curl}
          onValueChange={setCurl}
          minimumTrackTintColor={colors.primary}
          maximumTrackTintColor={colors.border}
          thumbTintColor={colors.primary}
        />
      </View>

      <Text style={styles.sliderLabel}>发色: {COLORS.find((c) => c.name === color)?.label}</Text>
      <View style={styles.colorRow}>
        {COLORS.map((c) => (
          <TouchableOpacity
            key={c.name}
            style={[
              styles.colorDot,
              { backgroundColor: c.color },
              color === c.name && styles.colorDotSelected,
            ]}
            onPress={() => setColor(c.name)}
            accessibilityRole="button"
            accessibilityLabel={c.label}
          />
        ))}
      </View>

      <TouchableOpacity
        style={[styles.regenerateBtn, loading && styles.regenerateBtnDisabled]}
        onPress={() => onRegenerate({ length, curl, color })}
        disabled={loading}
        accessibilityRole="button"
        accessibilityLabel="重新生成"
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.regenerateText}>重新生成</Text>
        )}
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    padding: spacing.lg,
    marginTop: spacing.md,
    width: '100%',
    maxWidth: 400,
    alignSelf: 'center',
    borderWidth: 1,
    borderColor: colors.border,
  },
  sectionTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: colors.text,
    marginBottom: spacing.md,
  },
  sliderRow: {
    marginBottom: spacing.md,
  },
  sliderLabel: {
    fontSize: 13,
    color: colors.textSecondary,
    marginBottom: 4,
  },
  slider: {
    width: '100%',
    height: 40,
  },
  colorRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginVertical: spacing.md,
    flexWrap: 'wrap',
  },
  colorDot: {
    width: 32,
    height: 32,
    borderRadius: 16,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  colorDotSelected: {
    borderColor: colors.primary,
    borderWidth: 3,
  },
  regenerateBtn: {
    backgroundColor: colors.primary,
    paddingVertical: 12,
    borderRadius: radii.sm,
    alignItems: 'center',
    marginTop: spacing.sm,
  },
  regenerateBtnDisabled: {
    opacity: 0.6,
  },
  regenerateText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '600',
  },
});
