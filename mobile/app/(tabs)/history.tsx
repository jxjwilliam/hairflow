import React, { useCallback, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Alert,
  RefreshControl,
} from 'react-native';
import { Image } from 'expo-image';
import { useFocusEffect, useRouter } from 'expo-router';
import {
  HistoryItem,
  clearHistory,
  loadHistory,
  removeHistoryItem,
} from '../../services/history';
import { useLayout } from '../../hooks/useLayout';
import { colors, radii, spacing, THUMB_ASPECT } from '../../constants/theme';

export default function HistoryScreen() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const { columns, cardWidth, gutter, horizontalPad, contentWidth } = useLayout();
  const router = useRouter();

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      setItems(await loadHistory());
    } finally {
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      void refresh();
    }, [refresh]),
  );

  const handleClear = () => {
    Alert.alert('清空效果图？', '将删除本机保存的试戴记录（不影响服务器文件）', [
      { text: '取消', style: 'cancel' },
      {
        text: '清空',
        style: 'destructive',
        onPress: async () => {
          await clearHistory();
          setItems([]);
        },
      },
    ]);
  };

  if (items.length === 0) {
    return (
      <View style={styles.empty}>
        <Text style={styles.emptyTitle}>还没有试戴记录</Text>
        <Text style={styles.emptyHint}>在「发型」里选一款并生成后，效果会出现在这里，方便对比</Text>
        <TouchableOpacity style={styles.cta} onPress={() => router.push('/(tabs)')}>
          <Text style={styles.ctaText}>去选发型</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View
        style={[
          styles.toolbar,
          {
            paddingHorizontal: horizontalPad,
            maxWidth: contentWidth,
            width: '100%',
            alignSelf: 'center',
          },
        ]}
      >
        <Text style={styles.count}>共 {items.length} 张</Text>
        <TouchableOpacity onPress={handleClear}>
          <Text style={styles.clear}>清空</Text>
        </TouchableOpacity>
      </View>

      <FlatList
        data={items}
        key={columns}
        keyExtractor={(item) => item.id}
        numColumns={columns}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} />}
        contentContainerStyle={[
          styles.list,
          {
            paddingHorizontal: horizontalPad,
            maxWidth: contentWidth,
            width: '100%',
            alignSelf: 'center',
          },
        ]}
        renderItem={({ item, index }) => {
          const isEndOfRow = (index + 1) % columns === 0;
          return (
          <TouchableOpacity
            style={[
              styles.card,
              { width: cardWidth, marginRight: isEndOfRow ? 0 : gutter, marginBottom: gutter },
            ]}
            onPress={() =>
              router.push({
                pathname: '/result-view',
                params: {
                  imageUrl: item.imageUrl,
                  templateName: item.templateName,
                },
              })
            }
            onLongPress={() => {
              Alert.alert(item.templateName, '删除这张效果图？', [
                { text: '取消', style: 'cancel' },
                {
                  text: '删除',
                  style: 'destructive',
                  onPress: () => {
                    void removeHistoryItem(item.id).then(setItems);
                  },
                },
              ]);
            }}
            activeOpacity={0.9}
          >
            <Image
              source={{ uri: item.imageUrl }}
              style={{ width: cardWidth, height: cardWidth / THUMB_ASPECT }}
              contentFit="cover"
            />
            <View style={styles.meta}>
              <Text style={styles.name} numberOfLines={1}>
                {item.templateName}
              </Text>
              <Text style={styles.time}>
                {new Date(item.createdAt).toLocaleString()}
              </Text>
            </View>
          </TouchableOpacity>
          );
        }}      />
      <Text style={styles.hint}>长按可删除单张 · 下拉刷新</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  empty: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.xl,
    backgroundColor: colors.bg,
  },
  emptyTitle: { fontSize: 18, fontWeight: '700', color: colors.text, marginBottom: spacing.sm },
  emptyHint: {
    fontSize: 14,
    color: colors.textSecondary,
    textAlign: 'center',
    marginBottom: spacing.xl,
    maxWidth: 320,
    lineHeight: 20,
  },
  cta: {
    backgroundColor: colors.primary,
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: radii.sm,
  },
  ctaText: { color: '#fff', fontWeight: '600', fontSize: 15 },
  toolbar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.sm,
  },
  count: { fontSize: 13, color: colors.textSecondary },
  clear: { fontSize: 13, color: colors.danger, fontWeight: '600' },
  list: { paddingBottom: 40 },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    overflow: 'hidden',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
  },
  meta: { padding: spacing.sm },
  name: { fontSize: 13, fontWeight: '600', color: colors.text },
  time: { fontSize: 11, color: colors.textMuted, marginTop: 2 },
  hint: {
    textAlign: 'center',
    fontSize: 11,
    color: colors.textMuted,
    paddingBottom: spacing.md,
  },
});
