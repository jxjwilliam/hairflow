import React from 'react';
import { Image, StyleSheet, Dimensions } from 'react-native';

const { width } = Dimensions.get('window');

interface Props {
  imageUrl: string;
}

export default function ResultView({ imageUrl }: Props) {
  return (
    <Image
      source={{ uri: imageUrl }}
      style={styles.image}
      resizeMode="contain"
    />
  );
}

const styles = StyleSheet.create({
  image: { width: width, height: width * 1.3, borderRadius: 12 },
});
