import React, { useState } from 'react';
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { useQuery } from '@tanstack/react-query';
import { fetchTemplates } from '../../services/templates';
import CategoryTabs from '../../components/CategoryTabs';
import TemplateGrid from '../../components/TemplateGrid';
import { Template } from '../../types';

export default function HomeScreen() {
  const [category, setCategory] = useState('');
  const router = useRouter();

  const { data: templates = [], isLoading, isError, error } = useQuery({
    queryKey: ['templates', category],
    queryFn: () => fetchTemplates(category || undefined),
  });

  const handleSelect = (template: Template) => {
    router.push({ pathname: '/capture', params: { templateId: template.id } });
  };

  if (isLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#6366f1" />
        <Text style={styles.loadingText}>加载中...</Text>
      </View>
    );
  }

  if (isError) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorIcon}>⚠️</Text>
        <Text style={styles.errorTitle}>连接失败</Text>
        <Text style={styles.errorDetail}>
          {error instanceof Error ? error.message : '无法连接到服务器'}
        </Text>
        <Text style={styles.errorHint}>
          请确认后端已启动（uvicorn app.main:app --host 0.0.0.0 --port 8000）
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <CategoryTabs selected={category} onSelect={setCategory} />
      <TemplateGrid templates={templates} onSelect={handleSelect} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8f9fa' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#f8f9fa', padding: 24 },
  loadingText: { marginTop: 12, fontSize: 16, color: '#666' },
  errorIcon: { fontSize: 48, marginBottom: 16 },
  errorTitle: { fontSize: 20, fontWeight: '600', color: '#333', marginBottom: 8 },
  errorDetail: { fontSize: 14, color: '#666', textAlign: 'center', marginBottom: 12 },
  errorHint: { fontSize: 12, color: '#999', textAlign: 'center' },
});
