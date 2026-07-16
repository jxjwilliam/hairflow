import React, { useState } from 'react';
import { View, StyleSheet } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import PhotoCapture from '../components/PhotoCapture';

export default function CaptureScreen() {
  const { templateId } = useLocalSearchParams<{ templateId: string }>();
  const [photoUri, setPhotoUri] = useState<string | null>(null);
  const [photoBase64, setPhotoBase64] = useState<string>('');
  const router = useRouter();

  const handlePhotoTaken = (base64: string, uri: string) => {
    setPhotoBase64(base64);
    setPhotoUri(uri);
    router.replace({
      pathname: '/preview',
      params: { templateId, photoBase64: base64 },
    });
  };

  return (
    <View style={styles.container}>
      <PhotoCapture photoUri={photoUri} onPhotoTaken={handlePhotoTaken} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
});
