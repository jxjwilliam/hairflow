import React, { useMemo, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useMutation } from '@tanstack/react-query';
import { Video, ResizeMode } from 'expo-av';
import ResultView from '../components/ResultView';
import ActionButtons from '../components/ActionButtons';
import LoadingOverlay from '../components/LoadingOverlay';
import { generateVideo } from '../services/generation';
import { colors, spacing, radii } from '../constants/theme';
import type { GenerationOptions } from '../types';

const PIPELINE_LABELS: Record<string, string> = {
  photomaker: 'PhotoMaker v1',
  sd15: 'Realistic Vision',
  flux: 'FLUX.1 Schnell',
  flux_klein: 'FLUX.2 Klein 4B',
};

const METHOD_LABELS: Record<string, string> = {
  photomaker: '保持人脸',
  txt2img: '文本生成',
  img2img: '图生图',
};

/** View a saved result without re-running generation */
export default function ResultViewScreen() {
  const { imageUrl, templateName, generationOptions, createdAt } = useLocalSearchParams<{
    imageUrl: string;
    templateName?: string;
    generationOptions?: string;
    createdAt?: string;
  }>();
  const router = useRouter();
  const [videoUrl, setVideoUrl] = useState<string | null>(null);

  const options: GenerationOptions | null = useMemo(() => {
    if (!generationOptions) return null;
    try {
      const p = JSON.parse(generationOptions);
      if (
        typeof p?.pipeline === 'string' &&
        typeof p?.method === 'string' &&
        typeof p?.steps === 'number'
      ) {
        return p as GenerationOptions;
      }
    } catch {
      // ignore malformed history metadata
    }
    return null;
  }, [generationOptions]);

  const createdDate: Date | null = useMemo(() => {
    if (!createdAt) return null;
    const ts = parseInt(createdAt, 10);
    return Number.isNaN(ts) ? null : new Date(ts);
  }, [createdAt]);

  const videoMutation = useMutation({
    mutationFn: () => generateVideo({ imageUrl: imageUrl! }),
    onSuccess: (data) => {
      setVideoUrl(data.video_url);
    },
    onError: () => {
      alert('短视频生成失败，请确认 ComfyUI 已启动且视频模型可用');
    },
  });

  if (!imageUrl) {
    return (
      <View style={styles.empty}>
        <Text style={styles.emptyText}>找不到效果图</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {videoMutation.isPending && (
        <LoadingOverlay message="正在生成短视频（本机可能需要数分钟）…" />
      )}
      <ScrollView contentContainerStyle={styles.scroll}>
        {templateName ? <Text style={styles.label}>{templateName}</Text> : null}
        <ResultView imageUrl={imageUrl} />

        {options && (
          <View style={styles.metaCard}>
            <Text style={styles.metaTitle}>生成参数</Text>
            <View style={styles.metaDivider} />
            <MetaRow label="模型" value={PIPELINE_LABELS[options.pipeline] || options.pipeline} />
            <MetaRow label="方式" value={METHOD_LABELS[options.method] || options.method} />
            <MetaRow
              label="变化程度"
              value={`${Math.round(options.denoise * 100)}%`}
            />
            <MetaRow label="步数" value={`${options.steps}`} />
            <MetaRow
              label="CFG"
              value={options.pipeline.startsWith('flux') ? '1.0（固定）' : String(options.cfg)}
            />
            {createdDate && (
              <MetaRow
                label="生成时间"
                value={createdDate.toLocaleString()}
              />
            )}
          </View>
        )}

        <TouchableOpacity
          style={[
            styles.videoButton,
            videoMutation.isPending && styles.videoButtonDisabled,
          ]}
          onPress={() => videoMutation.mutate()}
          disabled={videoMutation.isPending}
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

        <ActionButtons
          imageUrl={imageUrl}
          onTryAnotherStyle={() => router.replace('/')}
          onBackHome={() => router.replace('/')}
        />
      </ScrollView>
    </View>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.metaRow}>
      <Text style={styles.metaLabel}>{label}</Text>
      <Text style={styles.metaValue}>{value}</Text>
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
  label: { fontSize: 16, fontWeight: '600', color: colors.text, marginBottom: spacing.sm },
  empty: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  emptyText: { color: colors.textSecondary },
  metaCard: {
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    padding: spacing.md,
    marginTop: spacing.md,
    alignSelf: 'stretch',
    marginHorizontal: spacing.lg,
  },
  metaTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.text,
    marginBottom: spacing.xs,
  },
  metaDivider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: colors.border,
    marginBottom: spacing.sm,
  },
  metaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 3,
  },
  metaLabel: {
    fontSize: 13,
    color: colors.textSecondary,
  },
  metaValue: {
    fontSize: 13,
    color: colors.text,
    fontWeight: '500',
  },
  videoButton: {
    backgroundColor: colors.primary,
    borderRadius: 8,
    marginTop: spacing.md,
    marginHorizontal: spacing.lg,
    alignSelf: 'stretch',
    alignItems: 'center',
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
});
