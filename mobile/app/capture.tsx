import React, { useState } from 'react';
import { View, StyleSheet } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import PhotoCapture from '../components/PhotoCapture';
import { useSession } from '../context/SessionContext';
import { colors } from '../constants/theme';

export default function CaptureScreen() {
  const { templateId, templateName } = useLocalSearchParams<{
    templateId: string;
    templateName?: string;
  }>();
  const [photoUri, setPhotoUri] = useState<string | null>(null);
  const router = useRouter();
  const { setPhoto } = useSession();

  const handlePhotoTaken = (base64: string, uri: string) => {
    setPhotoUri(uri);
    setPhoto({ base64, uri });
    router.replace({
      pathname: '/preview',
      params: {
        templateId,
        templateName: templateName ?? '',
        photoBase64: base64,
      },
    });
  };

  return (
    <View style={styles.container}>
      <PhotoCapture
        photoUri={photoUri}
        onPhotoTaken={handlePhotoTaken}
        templateName={templateName}
        onBack={() => router.back()}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
});
