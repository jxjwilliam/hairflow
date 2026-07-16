import React, { useState, useEffect } from 'react';
import { View, StyleSheet, SafeAreaView } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { useMutation } from '@tanstack/react-query';
import { generateHairstyle } from '../services/generation';
import LoadingOverlay from '../components/LoadingOverlay';
import ResultView from '../components/ResultView';
import ActionButtons from '../components/ActionButtons';

export default function PreviewScreen() {
  const { templateId, photoBase64 } = useLocalSearchParams<{
    templateId: string;
    photoBase64: string;
  }>();
  const [resultUrl, setResultUrl] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => generateHairstyle(photoBase64!, templateId!),
    onSuccess: (data) => setResultUrl(data.image_url),
    onError: () => alert('生成失败，请重试'),
  });

  useEffect(() => {
    if (photoBase64 && templateId) {
      mutation.mutate();
    }
  }, []);

  return (
    <SafeAreaView style={styles.container}>
      {mutation.isPending && <LoadingOverlay message="AI 正在生成发型效果图..." />}

      {resultUrl && (
        <>
          <ResultView imageUrl={resultUrl} />
          <ActionButtons
            imageUrl={resultUrl}
            onRetry={() => mutation.mutate()}
          />
        </>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff', alignItems: 'center', justifyContent: 'center' },
});
