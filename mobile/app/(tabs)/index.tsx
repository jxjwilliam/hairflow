import React, { useState } from 'react';
import { View, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { useQuery } from '@tanstack/react-query';
import { fetchTemplates } from '../../services/templates';
import CategoryTabs from '../../components/CategoryTabs';
import TemplateGrid from '../../components/TemplateGrid';
import { Template } from '../../types';

export default function HomeScreen() {
  const [category, setCategory] = useState('');
  const router = useRouter();

  const { data: templates = [] } = useQuery({
    queryKey: ['templates', category],
    queryFn: () => fetchTemplates(category || undefined),
  });

  const handleSelect = (template: Template) => {
    router.push({ pathname: '/capture', params: { templateId: template.id } });
  };

  return (
    <View style={styles.container}>
      <CategoryTabs selected={category} onSelect={setCategory} />
      <TemplateGrid templates={templates} onSelect={handleSelect} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8f9fa' },
});
