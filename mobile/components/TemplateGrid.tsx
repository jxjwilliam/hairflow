import React from 'react';
import { FlatList, StyleSheet } from 'react-native';
import TemplateCard from './TemplateCard';
import { Template } from '../types';

interface Props {
  templates: Template[];
  onSelect: (t: Template) => void;
}

export default function TemplateGrid({ templates, onSelect }: Props) {
  return (
    <FlatList
      data={templates}
      keyExtractor={(item) => item.id}
      numColumns={2}
      renderItem={({ item }) => <TemplateCard template={item} onPress={onSelect} />}
      contentContainerStyle={styles.list}
      columnWrapperStyle={styles.row}
    />
  );
}

const styles = StyleSheet.create({
  list: { padding: 6 },
  row: { justifyContent: 'space-between' },
});
