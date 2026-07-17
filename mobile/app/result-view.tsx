import React from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import ResultView from '../components/ResultView';
import ActionButtons from '../components/ActionButtons';
import { colors, spacing } from '../constants/theme';

/** View a saved result without re-running generation */
export default function ResultViewScreen() {
  const { imageUrl, templateName } = useLocalSearchParams<{
    imageUrl: string;
    templateName?: string;
  }>();
  const router = useRouter();

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
      <ActionButtons
        imageUrl={imageUrl}
        onTryAnotherStyle={() => router.replace('/(tabs)')}
        onBackHome={() => router.replace('/(tabs)')}
      />
    </ScrollView>
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
});
