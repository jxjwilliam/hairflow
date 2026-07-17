import React from 'react';
import { ScrollView, TouchableOpacity, Text, StyleSheet, View } from 'react-native';
import { colors, radii, spacing } from '../constants/theme';
import { useLayout } from '../hooks/useLayout';

const CATEGORIES = [
  { key: '', label: '全部' },
  { key: 'men', label: '男士' },
  { key: 'women', label: '女士' },
];

interface Props {
  selected: string;
  onSelect: (key: string) => void;
}

export default function CategoryTabs({ selected, onSelect }: Props) {
  const { horizontalPad, contentWidth } = useLayout();

  return (
    <View style={styles.wrap}>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={[
          styles.container,
          { paddingHorizontal: horizontalPad, maxWidth: contentWidth, alignSelf: 'center', width: '100%' },
        ]}
      >
        {CATEGORIES.map((cat) => {
          const active = selected === cat.key;
          return (
            <TouchableOpacity
              key={cat.key}
              style={[styles.pill, active && styles.pillActive]}
              onPress={() => onSelect(cat.key)}
              accessibilityRole="button"
              accessibilityLabel={`筛选${cat.label}`}
              accessibilityState={{ selected: active }}
            >
              <Text style={[styles.pillText, active && styles.pillTextActive]}>{cat.label}</Text>
            </TouchableOpacity>
          );
        })}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
    backgroundColor: colors.surface,
  },
  container: {
    paddingVertical: spacing.sm + 2,
    gap: spacing.sm,
    flexDirection: 'row',
  },
  pill: {
    paddingHorizontal: 18,
    paddingVertical: 8,
    borderRadius: radii.pill,
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  pillActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  pillText: { fontSize: 14, color: colors.textSecondary, fontWeight: '500' },
  pillTextActive: { color: '#fff', fontWeight: '600' },
});
