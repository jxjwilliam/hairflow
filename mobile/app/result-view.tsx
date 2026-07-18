import React, { useMemo } from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import ResultView from '../components/ResultView';
import ActionButtons from '../components/ActionButtons';
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
    } catch {}
    return null;
  }, [generationOptions]);

  const createdDate: Date | null = useMemo(() => {
    if (!createdAt) return null;
    const ts = parseInt(createdAt, 10);
    return Number.isNaN(ts) ? null : new Date(ts);
  }, [createdAt]);

  if (!imageUrl) {
    return (
      <View style={styles.empty}>
        <Text style={styles.emptyText}>找不到效果图</Text>
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.scroll} style={styles.container}>
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

      <ActionButtons
        imageUrl={imageUrl}
        onTryAnotherStyle={() => router.replace('/')}
        onBackHome={() => router.replace('/')}
      />
    </ScrollView>
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
});
