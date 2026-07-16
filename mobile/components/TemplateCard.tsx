import React from 'react';
import { TouchableOpacity, Text, View, StyleSheet } from 'react-native';
import { Image } from 'expo-image';
import { Template } from '../types';

interface Props {
  template: Template;
  onPress: (t: Template) => void;
}

const blurhash = 'L6PZfSi_.AyE_3t7t7R**0o#DgR4';

export default function TemplateCard({ template, onPress }: Props) {
  return (
    <TouchableOpacity style={styles.card} onPress={() => onPress(template)}>
      <Image
        source={{ uri: template.thumbnail }}
        style={styles.image}
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
    flex: 1,
    margin: 6,
    backgroundColor: '#fff',
    borderRadius: 12,
    overflow: 'hidden',
    boxShadow: '0 1px 4px rgba(0,0,0,0.1)',
  },
  image: { width: '100%', height: 160 },
  info: { padding: 10 },
  name: { fontSize: 14, fontWeight: '600' },
  desc: { fontSize: 12, color: '#888', marginTop: 2 },
});
