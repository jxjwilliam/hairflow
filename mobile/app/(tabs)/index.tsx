import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, TouchableOpacity } from 'react-native';
import { useRouter } from 'expo-router';
import { useQuery } from '@tanstack/react-query';
import { fetchTemplates } from '../../services/templates';
import CategoryTabs from '../../components/CategoryTabs';
import TemplateGrid from '../../components/TemplateGrid';
import FocusedScreen from '../../components/FocusedScreen';
import { Template } from '../../types';
import { useSession } from '../../context/SessionContext';
import { colors, spacing, radii } from '../../constants/theme';
import { useLayout } from '../../hooks/useLayout';

export default function HomeScreen() {
  const [category, setCategory] = useState('');
  const router = useRouter();
  const { photo, clearPhoto } = useSession();
  const { horizontalPad, contentWidth } = useLayout();

  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.title = '发型库 · 发型试戴';
    }
  }, []);

  const { data: templates = [], isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['templates', category],
    queryFn: () => fetchTemplates(category || undefined),
  });

  const handleSelect = (template: Template) => {
    if (photo?.base64) {
      router.push({
        pathname: '/preview',
        params: {
          templateId: template.id,
          templateName: template.name,
          photoBase64: photo.base64,
        },
      });
      return;
    }
    router.push({
      pathname: '/capture',
      params: { templateId: template.id, templateName: template.name },
    });
  };

  if (isLoading) {
    return (
      <FocusedScreen tab="index" style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>加载发型模板…</Text>
      </FocusedScreen>
    );
  }

  if (isError) {
    return (
      <FocusedScreen tab="index" style={styles.center}>
        <Text style={styles.errorTitle}>无法加载发型库</Text>
        <Text style={styles.errorDetail}>
          {error instanceof Error ? error.message : '无法连接到服务器'}
        </Text>
        <Text style={styles.errorHint}>请确认后端已启动（端口 8000），然后重试</Text>
        <TouchableOpacity style={styles.retryBtn} onPress={() => refetch()}>
          <Text style={styles.retryText}>{isFetching ? '重试中…' : '重新加载'}</Text>
        </TouchableOpacity>
      </FocusedScreen>
    );
  }

  return (
    <FocusedScreen tab="index" style={styles.container}>
      <View
        style={[
          styles.intro,
          {
            paddingHorizontal: horizontalPad,
            maxWidth: contentWidth,
            width: '100%',
            alignSelf: 'center',
          },
        ]}
      >
        <Text style={styles.introTitle}>选择一款发型开始试戴</Text>
        <Text style={styles.introHint}>
          {photo
            ? '已保存你的照片：点选发型即可直接生成'
            : '点选卡片 → 上传正面照 → AI 生成效果'}
        </Text>
      </View>

      {photo && (
        <View
          style={[
            styles.banner,
            {
              paddingHorizontal: horizontalPad,
              maxWidth: contentWidth,
              width: '100%',
              alignSelf: 'center',
            },
          ]}
        >
          <Text style={styles.bannerText}>照片已保留，可连续试戴多款发型</Text>
          <TouchableOpacity onPress={clearPhoto} accessibilityRole="button">
            <Text style={styles.bannerAction}>清除照片</Text>
          </TouchableOpacity>
        </View>
      )}

      <CategoryTabs selected={category} onSelect={setCategory} />
      <TemplateGrid templates={templates} onSelect={handleSelect} />
    </FocusedScreen>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.bg,
    padding: spacing.xl,
  },
  loadingText: { marginTop: spacing.md, fontSize: 16, color: colors.textSecondary },
  errorTitle: { fontSize: 20, fontWeight: '600', color: colors.text, marginBottom: spacing.sm },
  errorDetail: {
    fontSize: 14,
    color: colors.textSecondary,
    textAlign: 'center',
    marginBottom: spacing.md,
  },
  errorHint: { fontSize: 12, color: colors.textMuted, textAlign: 'center', marginBottom: spacing.lg },
  retryBtn: {
    backgroundColor: colors.primary,
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: radii.sm,
  },
  retryText: { color: '#fff', fontWeight: '600' },
  intro: {
    paddingTop: spacing.md,
    paddingBottom: spacing.sm,
  },
  introTitle: { fontSize: 18, fontWeight: '700', color: colors.text },
  introHint: { fontSize: 13, color: colors.textSecondary, marginTop: 4, lineHeight: 18 },
  banner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.md,
    paddingVertical: spacing.sm + 2,
    backgroundColor: colors.primarySoft,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  bannerText: { flex: 1, fontSize: 13, color: colors.primary, fontWeight: '500' },
  bannerAction: {
    fontSize: 13,
    color: colors.primary,
    fontWeight: '700',
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
  },
});
