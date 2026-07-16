import React from 'react';
import { ScrollView, TouchableOpacity, Text, StyleSheet } from 'react-native';

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
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.container}>
      {CATEGORIES.map((cat) => (
        <TouchableOpacity
          key={cat.key}
          style={[styles.pill, selected === cat.key && styles.pillActive]}
          onPress={() => onSelect(cat.key)}
        >
          <Text style={[styles.pillText, selected === cat.key && styles.pillTextActive]}>
            {cat.label}
          </Text>
        </TouchableOpacity>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { paddingHorizontal: 16, paddingVertical: 8 },
  pill: {
    paddingHorizontal: 20,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: '#f0f0f0',
    marginRight: 8,
  },
  pillActive: { backgroundColor: '#2563eb' },
  pillText: { fontSize: 14, color: '#666' },
  pillTextActive: { color: '#fff', fontWeight: '600' },
});
