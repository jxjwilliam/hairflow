import React, { useCallback, useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { colors, spacing, radii } from '../constants/theme';
import {
  fetchTiers,
  fetchMembershipStatus,
  upgradeMembership,
  TierInfo,
  MembershipStatus,
} from '../services/membership';

const TIER_ORDER = ['free', 'pro', 'premium'];

function tierColor(tier: string) {
  if (tier === 'premium') return colors.tierPremium;
  if (tier === 'pro') return colors.tierPro;
  return colors.tierFree;
}

function tierBg(tier: string) {
  if (tier === 'premium') return colors.tierPremiumBg;
  if (tier === 'pro') return colors.tierProBg;
  return colors.tierFreeBg;
}

function tierBadge(tier: string) {
  if (tier === 'premium') return 'PREMIUM';
  if (tier === 'pro') return 'PRO';
  return 'FREE';
}

export default function MembershipScreen() {
  const router = useRouter();
  const [tiers, setTiers] = useState<TierInfo[]>([]);
  const [status, setStatus] = useState<MembershipStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState<string | null>(null);
  const [message, setMessage] = useState('');

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [tiersData, statusData] = await Promise.all([
        fetchTiers(),
        fetchMembershipStatus().catch(() => null),
      ]);
      setTiers(tiersData);
      setStatus(statusData);
    } catch {
      setMessage('加载失败，请确认后端已启动');
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      void loadData();
    }, [loadData]),
  );

  const handleUpgrade = async (tierId: string) => {
    setUpgrading(tierId);
    setMessage('');
    try {
      const result = await upgradeMembership(tierId, 'mock');
      setMessage(`成功升级为 ${tierId === 'premium' ? 'Premium' : 'Pro'} 会员！`);
      await loadData();
    } catch {
      setMessage('升级失败，请重试');
    } finally {
      setUpgrading(null);
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  const currentTier = status?.tier || 'free';

  // Sort tiers in logical order: free → pro → premium
  const sortedTiers = [...tiers].sort(
    (a, b) => TIER_ORDER.indexOf(a.id) - TIER_ORDER.indexOf(b.id),
  );

  return (
    <ScrollView contentContainerStyle={styles.container}>
      {/* Current status card */}
      <View style={styles.statusCard}>
        <View
          style={[
            styles.badge,
            { backgroundColor: tierBg(currentTier) },
          ]}
        >
          <Text style={[styles.badgeText, { color: tierColor(currentTier) }]}>
            {tierBadge(currentTier)}
          </Text>
        </View>
        <Text style={styles.statusLabel}>
          {status?.label || '免费用户'}
        </Text>
        {currentTier !== 'free' && status?.expires_at && (
          <Text style={styles.expiresText}>
            有效期至: {new Date(status.expires_at).toLocaleDateString('zh-CN')}
          </Text>
        )}
        <View style={styles.statRow}>
          <View style={styles.statItem}>
            <Text style={styles.statValue}>{status?.points_balance ?? 0}</Text>
            <Text style={styles.statLabel}>当前点数</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statItem}>
            <Text style={styles.statValue}>{status?.daily_left ?? 0}</Text>
            <Text style={styles.statLabel}>今日剩余</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statItem}>
            <Text style={styles.statValue}>{status?.max_points ?? 50}</Text>
            <Text style={styles.statLabel}>点数上限</Text>
          </View>
        </View>
      </View>

      <Text style={styles.sectionTitle}>选择会员方案</Text>

      {/* Tier cards */}
      <View style={styles.tierList}>
        {sortedTiers.map((tier) => {
          const isCurrent = tier.id === currentTier;
          const canUpgrade =
            tier.id !== 'free' &&
            (currentTier === 'free' ||
              TIER_ORDER.indexOf(tier.id) > TIER_ORDER.indexOf(currentTier));

          return (
            <View
              key={tier.id}
              style={[
                styles.tierCard,
                isCurrent && styles.tierCardCurrent,
                { borderColor: isCurrent ? tierColor(tier.id) : colors.border },
              ]}
            >
              {isCurrent && (
                <View style={[styles.currentFlag, { backgroundColor: tierColor(tier.id) }]}>
                  <Text style={styles.currentFlagText}>当前方案</Text>
                </View>
              )}
              <View style={styles.tierHeader}>
                <Text style={[styles.tierName, { color: tierColor(tier.id) }]}>
                  {tier.label}
                </Text>
                {tier.price > 0 && (
                  <Text style={styles.tierPrice}>
                    ¥{tier.price.toFixed(2)}
                    <Text style={styles.tierPriceUnit}> /月</Text>
                  </Text>
                )}
                {tier.price === 0 && (
                  <Text style={styles.tierPrice}>免费</Text>
                )}
              </View>

              <View style={styles.tierBenefits}>
                <Text style={styles.benefitItem}>
                  点数上限: {tier.max_points}
                </Text>
                <Text style={styles.benefitItem}>
                  每日免费: {tier.daily_free === 999 ? '不限' : `${tier.daily_free} 次`}
                </Text>
                {tier.price_discount < 1.0 && (
                  <Text style={styles.benefitItem}>
                    点数折扣: {Math.round((1 - tier.price_discount) * 100)}% OFF
                  </Text>
                )}
              </View>

              {canUpgrade && (
                <TouchableOpacity
                  style={[styles.upgradeBtn, { backgroundColor: tierColor(tier.id) }]}
                  onPress={() => handleUpgrade(tier.id)}
                  disabled={upgrading === tier.id}
                  accessibilityRole="button"
                  accessibilityLabel={`升级到${tier.label}`}
                >
                  {upgrading === tier.id ? (
                    <ActivityIndicator size="small" color="#fff" />
                  ) : (
                    <Text style={styles.upgradeBtnText}>升级</Text>
                  )}
                </TouchableOpacity>
              )}
            </View>
          );
        })}
      </View>

      {message ? (
        <Text
          style={message.includes('成功') ? styles.successMsg : styles.errorMsg}
        >
          {message}
        </Text>
      ) : null}

      <TouchableOpacity
        style={styles.backBtn}
        onPress={() => router.back()}
        accessibilityRole="button"
        accessibilityLabel="返回"
      >
        <Text style={styles.backText}>返回</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.bg,
  },
  container: {
    flexGrow: 1,
    backgroundColor: colors.bg,
    padding: spacing.xl,
    alignItems: 'center',
  },
  statusCard: {
    width: '100%',
    maxWidth: 400,
    backgroundColor: colors.surface,
    borderRadius: radii.lg,
    padding: spacing.xl,
    alignItems: 'center',
    marginBottom: spacing.xl,
    borderWidth: 1,
    borderColor: colors.border,
  },
  badge: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: radii.pill,
    marginBottom: spacing.sm,
  },
  badgeText: {
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 1,
  },
  statusLabel: {
    fontSize: 20,
    fontWeight: '700',
    color: colors.text,
    marginBottom: spacing.xs,
  },
  expiresText: {
    fontSize: 13,
    color: colors.textSecondary,
    marginBottom: spacing.md,
  },
  statRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: spacing.sm,
  },
  statItem: {
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
  },
  statValue: {
    fontSize: 22,
    fontWeight: '700',
    color: colors.text,
  },
  statLabel: {
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 2,
  },
  statDivider: {
    width: 1,
    height: 36,
    backgroundColor: colors.border,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: colors.text,
    marginBottom: spacing.md,
    alignSelf: 'flex-start',
    width: '100%',
    maxWidth: 400,
  },
  tierList: {
    width: '100%',
    maxWidth: 400,
    gap: spacing.md,
  },
  tierCard: {
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    padding: spacing.lg,
    borderWidth: 1.5,
    position: 'relative',
  },
  tierCardCurrent: {
    borderWidth: 2,
  },
  currentFlag: {
    position: 'absolute',
    top: -1,
    right: spacing.lg,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderBottomLeftRadius: radii.sm,
    borderBottomRightRadius: radii.sm,
  },
  currentFlagText: {
    color: '#fff',
    fontSize: 11,
    fontWeight: '700',
  },
  tierHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  tierName: {
    fontSize: 18,
    fontWeight: '700',
  },
  tierPrice: {
    fontSize: 20,
    fontWeight: '700',
    color: colors.text,
  },
  tierPriceUnit: {
    fontSize: 13,
    color: colors.textSecondary,
  },
  tierBenefits: {
    gap: 4,
    marginBottom: spacing.md,
  },
  benefitItem: {
    fontSize: 14,
    color: colors.textSecondary,
  },
  upgradeBtn: {
    borderRadius: radii.md,
    paddingVertical: spacing.sm + 2,
    alignItems: 'center',
  },
  upgradeBtnText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '700',
  },
  successMsg: {
    marginTop: spacing.lg,
    fontSize: 14,
    color: colors.success,
    textAlign: 'center',
  },
  errorMsg: {
    marginTop: spacing.lg,
    fontSize: 14,
    color: colors.danger,
    textAlign: 'center',
  },
  backBtn: {
    marginTop: spacing.xl,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.xl,
  },
  backText: {
    color: colors.textSecondary,
    fontSize: 14,
  },
});
