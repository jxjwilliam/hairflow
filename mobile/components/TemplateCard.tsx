import React from 'react';
import { TouchableOpacity, Image, Text, View, StyleSheet } from 'react-native';
import { Template } from '../types';

interface Props {
  template: Template;
  onPress: (t: Template) => void;
}

export default function TemplateCard({ template, onPress }: Props) {
  return (
    <TouchableOpacity style={styles.card} onPress={() => onPress(template)}>
      <Image source={{ uri: template.thumbnail }} style={styles.image} />
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
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  image: { width: '100%', height: 160, resizeMode: 'cover' },
  info: { padding: 10 },
  name: { fontSize: 14, fontWeight: '600' },
  desc: { fontSize: 12, color: '#888', marginTop: 2 },
});
