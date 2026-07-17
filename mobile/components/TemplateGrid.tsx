import React from 'react';
import { FlatList, StyleSheet, View } from 'react-native';
import TemplateCard from './TemplateCard';
import { Template } from '../types';
import { useLayout } from '../hooks/useLayout';

interface Props {
  templates: Template[];
  onSelect: (t: Template) => void;
}

export default function TemplateGrid({ templates, onSelect }: Props) {
  const { columns, cardWidth, gutter, horizontalPad, contentWidth } = useLayout();

  return (
    <View style={styles.shell}>
      <FlatList
        data={templates}
        key={columns}
        keyExtractor={(item) => item.id}
        numColumns={columns}
        renderItem={({ item, index }) => {
          const isEndOfRow = (index + 1) % columns === 0;
          return (
            <View
              style={{
                marginBottom: gutter,
                marginRight: isEndOfRow ? 0 : gutter,
              }}
            >
              <TemplateCard template={item} width={cardWidth} onPress={onSelect} />
            </View>
          );
        }}
        contentContainerStyle={[
          styles.list,
          {
            paddingHorizontal: horizontalPad,
            maxWidth: contentWidth,
            width: '100%',
            alignSelf: 'center',
          },
        ]}
        columnWrapperStyle={columns > 1 ? styles.row : undefined}
        showsVerticalScrollIndicator={false}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  shell: { flex: 1 },
  list: { paddingTop: 4, paddingBottom: 28 },
  row: { flexWrap: 'nowrap' },
});
