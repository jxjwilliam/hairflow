import React, { useCallback, useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Alert,
  Platform,
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
import { getCachedUser, fetchProfile, isLoggedIn } from '../../services/auth';
import { useLayout } from '../../hooks/useLayout';
import { colors, radii, spacing, THUMB_ASPECT } from '../../constants/theme';
import FocusedScreen from '../../components/FocusedScreen';

export default function HistoryScreen() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [loggedIn, setLoggedIn] = useState(false);
  const [pointsBalance, setPointsBalance] = useState<number | null>(null);
  const { columns, cardWidth, gutter, horizontalPad, contentWidth } = useLayout();
  const router = useRouter();

  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.title = '我的效果 · 发型试戴';
    }
  }, []);

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
      isLoggedIn().then(setLoggedIn);
      getCachedUser().then((u) => {
        if (u) setPointsBalance(u.points_balance);
      });
    }, [refresh]),
  );

  const handleRecharge = () => {
    router.push('/recharge');
  };

  const handleLogin = () => {
    router.push('/(auth)/login');
  };

  const handleClear = () => {
    const doClear = async () => {
      await clearHistory();
      setItems([]);
    };
    if (Platform.OS === 'web') {
      // RN Web Alert.alert only shows window.alert() - buttons never fire
      if (window.confirm('清空效果图？将删除本机保存的试戴记录（不影响服务器文件）')) {
        void doClear();
      }
    } else {
      Alert.alert('清空效果图？', '将删除本机保存的试戴记录（不影响服务器文件）', [
        { text: '取消', style: 'cancel' },
        { text: '清空', style: 'destructive', onPress: doClear },
      ]);
    }
  };

  if (items.length === 0) {
    return (
      <FocusedScreen tab="history" style={styles.empty}>
        <Text style={styles.emptyEmoji}>册</Text>
        <Text style={styles.emptyTitle}>还没有试戴记录</Text>
        <Text style={styles.emptyHint}>
          在「发型」里选一款并生成后，效果会出现在这里，方便对比不同发型
        </Text>
        <TouchableOpacity
          style={styles.cta}
          onPress={() => router.replace('/')}
          accessibilityRole="button"
          accessibilityLabel="去选发型"
        >
          <Text style={styles.ctaText}>去选发型</Text>
        </TouchableOpacity>
      </FocusedScreen>
    );
  }

  return (
    <FocusedScreen tab="history" style={styles.container}>
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
        <View>
          <Text style={styles.toolbarTitle}>我的效果</Text>
          <Text style={styles.count}>
            共 {items.length} 张{loggedIn && pointsBalance !== null ? ` · ⚡ ${pointsBalance} 点` : ''}
          </Text>
        </View>
        <View style={{ flexDirection: 'row', gap: 4, alignItems: 'center' }}>
          {loggedIn ? (
            <View style={{ flexDirection: 'row', gap: 4, alignItems: 'center' }}>
              <TouchableOpacity
                onPress={() => router.push('/membership')}
                accessibilityRole="button"
                accessibilityLabel="会员中心"
              >
                <Text style={styles.membershipBtn}>会员</Text>
              </TouchableOpacity>
              <TouchableOpacity
                onPress={handleRecharge}
                accessibilityRole="button"
                accessibilityLabel="购买点数"
              >
                <Text style={styles.recharge}>充值</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <TouchableOpacity
              onPress={handleLogin}
              accessibilityRole="button"
              accessibilityLabel="登录"
            >
              <Text style={styles.loginBtn}>登录</Text>
            </TouchableOpacity>
          )}
          <TouchableOpacity
            onPress={handleClear}
            accessibilityRole="button"
            accessibilityLabel="清空全部效果图"
          >
            <Text style={styles.clear}>清空</Text>
          </TouchableOpacity>
        </View>
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
                    ...(item.options ? { generationOptions: JSON.stringify(item.options) } : {}),
                    createdAt: String(item.createdAt),
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
              accessibilityRole="button"
              accessibilityLabel={`${item.templateName} 效果图`}
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
        }}
      />
      <Text style={styles.hint}>长按可删除单张 · 下拉刷新</Text>
    </FocusedScreen>
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
  emptyEmoji: {
    fontSize: 36,
    fontWeight: '700',
    color: colors.primary,
    marginBottom: spacing.md,
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
    paddingVertical: spacing.md,
  },
  toolbarTitle: { fontSize: 16, fontWeight: '700', color: colors.text },
  count: { fontSize: 12, color: colors.textSecondary, marginTop: 2 },
  loginBtn: { fontSize: 13, color: colors.primary, fontWeight: '600', padding: spacing.sm },
  membershipBtn: { fontSize: 13, color: colors.tierPro, fontWeight: '600', padding: spacing.sm },
  recharge: { fontSize: 13, color: colors.success, fontWeight: '600', padding: spacing.sm },
  clear: { fontSize: 13, color: colors.danger, fontWeight: '600', padding: spacing.sm },
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
