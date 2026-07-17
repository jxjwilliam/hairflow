import React from 'react';
import { TouchableOpacity, Text, View, StyleSheet } from 'react-native';
import { Image } from 'expo-image';
import { Template } from '../types';
import { colors, radii, spacing, THUMB_ASPECT } from '../constants/theme';

interface Props {
  template: Template;
  width: number;
  onPress: (t: Template) => void;
}

const blurhash = 'L6PZfSi_.AyE_3t7t7R**0o#DgR4';

export default function TemplateCard({ template, width, onPress }: Props) {
  return (
    <TouchableOpacity
      style={[styles.card, { width }]}
      onPress={() => onPress(template)}
      activeOpacity={0.85}
    >
      <Image
        source={{ uri: template.thumbnail }}
        style={[styles.image, { width, height: width / THUMB_ASPECT }]}
        placeholder={{ blurhash }}
        contentFit="cover"
        transition={200}
      />
      <View style={styles.info}>
        <Text style={styles.name} numberOfLines={1}>
          {template.name}
        </Text>
        <Text style={styles.desc} numberOfLines={2}>
          {template.description}
        </Text>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    overflow: 'hidden',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
  },
  image: {
    backgroundColor: colors.border,
  },
  info: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm + 2,
  },
  name: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.text,
  },
  desc: {
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 2,
    lineHeight: 16,
  },
});
