import React, { useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useMutation } from '@tanstack/react-query';
import { generateHairstyle } from '../services/generation';
import LoadingOverlay from '../components/LoadingOverlay';
import ResultView from '../components/ResultView';
import ActionButtons from '../components/ActionButtons';
import { addHistoryItem } from '../services/history';
import { useSession } from '../context/SessionContext';
import { colors, spacing } from '../constants/theme';

export default function PreviewScreen() {
  const { templateId, templateName, photoBase64 } = useLocalSearchParams<{
    templateId: string;
    templateName?: string;
    photoBase64: string;
  }>();
  const [resultUrl, setResultUrl] = useState<string | null>(null);
  const router = useRouter();
  const { clearPhoto } = useSession();
  const savedRef = useRef<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => generateHairstyle(photoBase64!, templateId!),
    onSuccess: async (data) => {
      setResultUrl(data.image_url);
      if (savedRef.current === data.image_url) return;
      savedRef.current = data.image_url;
      try {
        await addHistoryItem({
          imageUrl: data.image_url,
          templateId: templateId!,
          templateName: templateName || templateId || '发型',
          id: data.image_id,
        });
      } catch {
        // history is best-effort
      }
    },
    onError: () => {
      alert('生成失败，请确认后端与 ComfyUI 已启动后重试');
    },
  });

  useEffect(() => {
    if (photoBase64 && templateId) {
      mutation.mutate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- run once per screen mount
  }, []);

  return (
    <View style={styles.container}>
      {mutation.isPending && <LoadingOverlay message="AI 正在生成发型效果图…" />}

      {resultUrl && (
        <ScrollView
          contentContainerStyle={styles.scroll}
          showsVerticalScrollIndicator={false}
        >
          {templateName ? (
            <Text style={styles.label}>{templateName}</Text>
          ) : null}
          <ResultView imageUrl={resultUrl} />
          <ActionButtons
            imageUrl={resultUrl}
            onRetry={() => mutation.mutate()}
            onTryAnotherStyle={() => {
              // Keep session photo; return to catalog to pick another style
              router.replace('/');
            }}
            onRetakePhoto={() => {
              clearPhoto();
              router.replace({
                pathname: '/capture',
                params: {
                  templateId: templateId!,
                  templateName: templateName ?? '',
                },
              });
            }}
            onBackHome={() => {
              router.replace('/');
            }}
          />
        </ScrollView>
      )}

      {!mutation.isPending && !resultUrl && mutation.isError && (
        <View style={styles.errorBox}>
          <Text style={styles.errorTitle}>生成失败</Text>
          <Text style={styles.errorHint}>请确认后端与 ComfyUI 已启动</Text>
          <TouchableOpacity
            style={styles.retryBtn}
            onPress={() => mutation.mutate()}
            accessibilityRole="button"
            accessibilityLabel="重新生成"
          >
            <Text style={styles.retryText}>重新生成</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.homeLink}
            onPress={() => router.replace('/')}
            accessibilityRole="button"
            accessibilityLabel="返回发型库"
          >
            <Text style={styles.homeLinkText}>返回发型库</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  scroll: {
    flexGrow: 1,
    alignItems: 'center',
    paddingTop: spacing.md,
    paddingBottom: spacing.xxl,
  },
  label: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
    marginBottom: spacing.sm,
  },
  errorBox: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.xl,
    gap: spacing.sm,
  },
  errorTitle: { fontSize: 18, fontWeight: '600', color: colors.text },
  errorHint: {
    fontSize: 14,
    color: colors.textSecondary,
    textAlign: 'center',
    marginBottom: spacing.md,
  },
  retryBtn: {
    backgroundColor: colors.primary,
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
    marginTop: spacing.sm,
  },
  retryText: { color: '#fff', fontWeight: '600', fontSize: 15 },
  homeLink: { paddingVertical: spacing.sm, paddingHorizontal: spacing.md },
  homeLinkText: { color: colors.primary, fontWeight: '600', fontSize: 14 },
});
