import React, { useCallback, useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useMutation } from '@tanstack/react-query';
import { Video, ResizeMode } from 'expo-av';
import {
  generateHairstyle,
  regenerateHairstyle,
  generateMultiAngle,
  generateVideo,
} from '../services/generation';
import LoadingOverlay from '../components/LoadingOverlay';
import ResultView from '../components/ResultView';
import ActionButtons from '../components/ActionButtons';
import ParamPanel from '../components/ParamPanel';
import AngleSelector, { AngleKey } from '../components/AngleSelector';
import BeforeAfterSlider from '../components/BeforeAfterSlider';
import { addHistoryItem } from '../services/history';
import { useSession } from '../context/SessionContext';
import { colors, spacing } from '../constants/theme';
import { apiErrorMessage } from '../services/api';
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
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
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
      setVideoUrl(null);
      saveToHistory(data.image_url, 'single');
    },
    onError: (error) => {
      alert(apiErrorMessage(error, '生成失败，请确认后端与 ComfyUI 已启动后重试'));
    },
  });

  const multiAngleMutation = useMutation({
    mutationFn: () => generateMultiAngle(photoBase64!, templateId!, options),
    onSuccess: (data) => {
      setMultiAngleData(data.images);
      setResultUrl(data.images.front.url);
      setVideoUrl(null);
      setActiveAngle('front');
      setViewMode('multi');
      Object.values(data.images).forEach((img) => saveToHistory(img.url, 'front'));
    },
    onError: (error) => {
      alert(apiErrorMessage(error, '多角度生成失败'));
    },
  });

  const handleRegenerate = async (params: RegenerateParams) => {
    setRegenerating(true);
    try {
      const data = await regenerateHairstyle(photoBase64!, templateId!, params);
      setResultUrl(data.image_url);
      setVideoUrl(null);
      setMultiAngleData(null);
      setViewMode('single');
      saveToHistory(data.image_url, 'single');
    } catch (error) {
      alert(apiErrorMessage(error, '重新生成失败'));
    } finally {
      setRegenerating(false);
    }
  };

  const videoMutation = useMutation({
    mutationFn: () => generateVideo({ imageUrl: resultUrl! }),
    onSuccess: (data) => {
      setVideoUrl(data.video_url);
    },
    onError: (error) => {
      alert(apiErrorMessage(error, '短视频生成失败，请确认 ComfyUI 已启动且视频模型可用'));
    },
  });

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

  const isLoading = generateMutation.isPending
    || multiAngleMutation.isPending
    || videoMutation.isPending
    || regenerating;

  return (
    <View style={styles.container}>
      {isLoading && (
        <LoadingOverlay
          message={videoMutation.isPending ? '正在生成短视频（本机可能需要数分钟）…' : 'AI 正在生成发型效果图…'}
        />
      )}

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

          <TouchableOpacity
            style={[
              styles.videoButton,
              (!resultUrl || videoMutation.isPending) && styles.videoButtonDisabled,
            ]}
            onPress={() => videoMutation.mutate()}
            disabled={!resultUrl || videoMutation.isPending}
            accessibilityRole="button"
            accessibilityLabel="生成短视频"
          >
            <Text style={styles.videoButtonText}>生成短视频</Text>
          </TouchableOpacity>

          {videoUrl && (
            <Video
              source={{ uri: videoUrl }}
              useNativeControls
              resizeMode={ResizeMode.CONTAIN}
              style={styles.video}
            />
          )}
        </ScrollView>
      )}

      {!isLoading && !currentImageUrl && generateMutation.isError && (
        <View style={styles.errorBox}>
          <Text style={styles.errorTitle}>生成失败</Text>
          <Text style={styles.errorHint}>请确认后端与 ComfyUI 已启动</Text>
          <View style={styles.errorActions}>
            <TouchableOpacity
              style={styles.retryBtn}
              onPress={() => generateMutation.mutate()}
              accessibilityRole="button"
              accessibilityLabel="重新生成"
            >
              <Text style={styles.retryText}>重新生成</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.optionsBtn}
              onPress={() => router.replace({ pathname: '/options', params: { templateId, templateName, photoBase64 } })}
              accessibilityRole="button"
              accessibilityLabel="返回生成选项"
            >
              <Text style={styles.optionsBtnText}>返回生成选项</Text>
            </TouchableOpacity>
          </View>
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
  videoButton: {
    backgroundColor: colors.primary,
    borderRadius: 8,
    marginTop: spacing.md,
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.md,
  },
  videoButtonDisabled: { opacity: 0.55 },
  videoButtonText: { color: '#fff', fontSize: 15, fontWeight: '600' },
  video: {
    width: '100%',
    height: 360,
    marginTop: spacing.md,
    backgroundColor: '#000',
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
  errorActions: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: spacing.sm,
  },
  retryBtn: {
    backgroundColor: colors.primary,
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  retryText: { color: '#fff', fontWeight: '600', fontSize: 15 },
  optionsBtn: {
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
    borderWidth: 1.5,
    borderColor: colors.primary,
    backgroundColor: colors.surface,
  },
  optionsBtnText: { color: colors.primary, fontWeight: '600', fontSize: 15 },
  homeLink: { paddingVertical: spacing.sm, paddingHorizontal: spacing.md },
  homeLinkText: { color: colors.primary, fontWeight: '600', fontSize: 14 },
});
