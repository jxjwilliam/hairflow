import React, { useState } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, TouchableOpacity } from 'react-native';
import { useRouter } from 'expo-router';
import { useQuery } from '@tanstack/react-query';
import { fetchTemplates } from '../../services/templates';
import CategoryTabs from '../../components/CategoryTabs';
import TemplateGrid from '../../components/TemplateGrid';
import { Template } from '../../types';
import { useSession } from '../../context/SessionContext';
import { colors, spacing, radii } from '../../constants/theme';
import { useLayout } from '../../hooks/useLayout';

export default function HomeScreen() {
  const [category, setCategory] = useState('');
  const router = useRouter();
  const { photo, clearPhoto } = useSession();
  const { horizontalPad, contentWidth } = useLayout();

  const { data: templates = [], isLoading, isError, error } = useQuery({
    queryKey: ['templates', category],
    queryFn: () => fetchTemplates(category || undefined),
  });

  const handleSelect = (template: Template) => {
    if (photo?.base64) {
      // Reuse last photo — skip capture and generate immediately
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
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>加载发型模板…</Text>
      </View>
    );
  }

  if (isError) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorTitle}>连接失败</Text>
        <Text style={styles.errorDetail}>
          {error instanceof Error ? error.message : '无法连接到服务器'}
        </Text>
        <Text style={styles.errorHint}>
          请确认后端已启动，且 ComfyUI 在 8188 端口可用
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {photo && (
        <View
          style={[
            styles.banner,
            { paddingHorizontal: horizontalPad, maxWidth: contentWidth, alignSelf: 'center', width: '100%' },
          ]}
        >
          <Text style={styles.bannerText}>已保留你的照片 — 点选发型即可直接试戴</Text>
          <TouchableOpacity onPress={clearPhoto} accessibilityRole="button">
            <Text style={styles.bannerAction}>清除照片</Text>
          </TouchableOpacity>
        </View>
      )}
      <CategoryTabs selected={category} onSelect={setCategory} />
      <TemplateGrid templates={templates} onSelect={handleSelect} />
    </View>
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
  errorHint: { fontSize: 12, color: colors.textMuted, textAlign: 'center' },
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
    borderRadius: radii.sm,
  },
});
