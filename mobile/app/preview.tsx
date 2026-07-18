import React, { useCallback, useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useMutation } from '@tanstack/react-query';
import { generateHairstyle, regenerateHairstyle, generateMultiAngle } from '../services/generation';
import LoadingOverlay from '../components/LoadingOverlay';
import ResultView from '../components/ResultView';
import ActionButtons from '../components/ActionButtons';
import ParamPanel from '../components/ParamPanel';
import AngleSelector, { AngleKey } from '../components/AngleSelector';
import BeforeAfterSlider from '../components/BeforeAfterSlider';
import { addHistoryItem } from '../services/history';
import { useSession } from '../context/SessionContext';
import { colors, spacing } from '../constants/theme';
import type { GenerationOptions, RegenerateParams } from '../types';

type ViewMode = 'single' | 'multi' | 'compare';
type HistoryKey = 'single' | 'front';

export default function PreviewScreen() {
  const { templateId, templateName, photoBase64, generationOptions } = useLocalSearchParams<{
    templateId: string;
    templateName?: string;
    photoBase64: string;
    generationOptions?: string;
  }>();

  const options: GenerationOptions = React.useMemo(() => {
    if (generationOptions) {
      try { return JSON.parse(generationOptions); } catch {}
    }
    return { pipeline: 'photomaker', method: 'photomaker', denoise: 0.85, steps: 25, cfg: 6.5 };
  }, [generationOptions]);
  const router = useRouter();
  const { clearPhoto } = useSession();

  const [resultUrl, setResultUrl] = useState<string | null>(null);
  const [activeAngle, setActiveAngle] = useState<AngleKey>('front');
  const [multiAngleData, setMultiAngleData] = useState<Record<string, { url: string; id: string }> | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('single');
  const [regenerating, setRegenerating] = useState(false);
  const savedRef = useRef<Set<string>>(new Set());

  const saveToHistory = useCallback((url: string, key: HistoryKey = 'single') => {
    const dedupKey = `${key}:${url}`;
    if (savedRef.current.has(dedupKey)) return;
    savedRef.current.add(dedupKey);
    addHistoryItem({
      imageUrl: url,
      templateId: templateId!,
      templateName: templateName || templateId || '发型',
      id: `hist_${Date.now()}`,
      options,
    }).catch(() => {});
  }, [templateId, templateName, options]);

  const generateMutation = useMutation({
    mutationFn: () => generateHairstyle(photoBase64!, templateId!, options),
    onSuccess: (data) => {
      setResultUrl(data.image_url);
      saveToHistory(data.image_url, 'single');
    },
    onError: () => {
      alert('生成失败，请确认后端与 ComfyUI 已启动后重试');
    },
  });

  const multiAngleMutation = useMutation({
    mutationFn: () => generateMultiAngle(photoBase64!, templateId!, options),
    onSuccess: (data) => {
      setMultiAngleData(data.images);
      setResultUrl(data.images.front.url);
      setActiveAngle('front');
      setViewMode('multi');
      Object.values(data.images).forEach((img) => saveToHistory(img.url, 'front'));
    },
    onError: () => {
      alert('多角度生成失败');
    },
  });

  const handleRegenerate = async (params: RegenerateParams) => {
    setRegenerating(true);
    try {
      const data = await regenerateHairstyle(photoBase64!, templateId!, params);
      setResultUrl(data.image_url);
      setMultiAngleData(null);
      setViewMode('single');
      saveToHistory(data.image_url, 'single');
    } catch {
      alert('重新生成失败');
    } finally {
      setRegenerating(false);
    }
  };

  useEffect(() => {
    if (photoBase64 && templateId) {
      generateMutation.mutate();
    }
  }, []);

  const currentImageUrl = multiAngleData
    ? multiAngleData[activeAngle]?.url || resultUrl
    : resultUrl;

  const anglesArray = multiAngleData
    ? (Object.entries(multiAngleData) as [AngleKey, { url: string; id: string }][]).map(
        ([key, val]) => ({ key, label: key, url: val.url }),
      )
    : [];

  const isLoading = generateMutation.isPending || multiAngleMutation.isPending || regenerating;

  return (
    <View style={styles.container}>
      {isLoading && <LoadingOverlay message="AI 正在生成发型效果图…" />}

      {currentImageUrl && (
        <ScrollView
          contentContainerStyle={styles.scroll}
          showsVerticalScrollIndicator={false}
        >
          {templateName ? (
            <Text style={styles.label}>{templateName}</Text>
          ) : null}

          {viewMode === 'compare' ? (
            <BeforeAfterSlider
              beforeImage={`data:image/jpeg;base64,${photoBase64}`}
              afterImage={currentImageUrl}
            />
          ) : (
            <ResultView imageUrl={currentImageUrl} />
          )}

          {viewMode !== 'compare' && currentImageUrl && photoBase64 && (
            <TouchableOpacity
              style={styles.compareToggle}
              onPress={() => setViewMode('compare')}
              accessibilityRole="button"
              accessibilityLabel="原图对比"
            >
              <Text style={styles.compareToggleText}>原图对比</Text>
            </TouchableOpacity>
          )}

          {multiAngleData && viewMode !== 'compare' && (
            <AngleSelector
              angles={anglesArray}
              activeAngle={activeAngle}
              onAngleChange={(angle) => {
                setActiveAngle(angle);
                setViewMode('single');
              }}
            />
          )}

          <ParamPanel onRegenerate={handleRegenerate} loading={regenerating} />

          <ActionButtons
            imageUrl={currentImageUrl}
            onRetry={() => generateMutation.mutate()}
            onTryAnotherStyle={() => router.replace('/')}
            onRetakePhoto={() => {
              clearPhoto();
              router.replace({
                pathname: '/capture',
                params: { templateId: templateId!, templateName: templateName ?? '' },
              });
            }}
            onBackHome={() => router.replace('/')}
            extraActions={
              !multiAngleData
                ? [
                    {
                      label: '多角度生成',
                      onPress: () => multiAngleMutation.mutate(),
                      disabled: multiAngleMutation.isPending,
                    },
                  ]
                : undefined
            }
          />
        </ScrollView>
      )}

      {!isLoading && !currentImageUrl && generateMutation.isError && (
        <View style={styles.errorBox}>
          <Text style={styles.errorTitle}>生成失败</Text>
          <Text style={styles.errorHint}>请确认后端与 ComfyUI 已启动</Text>
          <TouchableOpacity
            style={styles.retryBtn}
            onPress={() => generateMutation.mutate()}
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
  compareToggle: {
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.lg,
  },
  compareToggleText: {
    color: colors.primary,
    fontSize: 13,
    fontWeight: '600',
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
