import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  ScrollView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { colors, spacing, radii } from '../constants/theme';
import { fetchPackages, createOrder, mockPay, Package } from '../services/payment';
import { getCachedUser, fetchProfile } from '../services/auth';

export default function RechargeScreen() {
  const [packages, setPackages] = useState<Package[]>([]);
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState(false);
  const [balance, setBalance] = useState<number | null>(null);
  const [message, setMessage] = useState('');
  const router = useRouter();

  useEffect(() => {
    const init = async () => {
      try {
        const [pkgs, user] = await Promise.all([
          fetchPackages(),
          getCachedUser(),
        ]);
        setPackages(pkgs);
        if (user) setBalance(user.points_balance);
      } catch {
        setMessage('加载失败，请确认后端已启动');
      } finally {
        setLoading(false);
      }
    };
    void init();
  }, []);

  const handlePurchase = async (pkg: Package) => {
    setPurchasing(true);
    setMessage('');
    try {
      const order = await createOrder(pkg.id, 'mock');
      const result = await mockPay(order.order_no);
      setBalance(result.balance_after);
      await fetchProfile();
      setMessage(`成功！获得 ${result.points_credited} 点，当前余额 ${result.balance_after} 点`);
    } catch {
      setMessage('购买失败，请重试');
    } finally {
      setPurchasing(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>购买点数</Text>
      {balance !== null && (
        <Text style={styles.balance}>当前余额: {balance} 点</Text>
      )}

      <View style={styles.pkgList}>
        {packages.map((pkg) => (
          <TouchableOpacity
            key={pkg.id}
            style={styles.pkgCard}
            onPress={() => handlePurchase(pkg)}
            disabled={purchasing}
            accessibilityRole="button"
            accessibilityLabel={`购买${pkg.name} ${pkg.points}点 ${pkg.price}元`}
          >
            <View style={styles.pkgInfo}>
              <Text style={styles.pkgName}>{pkg.name}</Text>
              <Text style={styles.pkgPoints}>{pkg.points} 点</Text>
            </View>
            <View style={styles.pkgPriceArea}>
              <Text style={styles.pkgPrice}>¥{pkg.price.toFixed(2)}</Text>
              {purchasing ? (
                <ActivityIndicator size="small" color={colors.primary} />
              ) : (
                <Text style={styles.buyText}>购买</Text>
              )}
            </View>
          </TouchableOpacity>
        ))}
      </View>

      {message ? (
        <Text style={message.includes('成功') ? styles.successMsg : styles.errorMsg}>
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
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: colors.bg },
  container: {
    flexGrow: 1,
    backgroundColor: colors.bg,
    padding: spacing.xl,
    alignItems: 'center',
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    color: colors.text,
    marginBottom: spacing.sm,
  },
  balance: {
    fontSize: 15,
    color: colors.textSecondary,
    marginBottom: spacing.xl,
  },
  pkgList: {
    width: '100%',
    maxWidth: 400,
    gap: spacing.md,
  },
  pkgCard: {
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    padding: spacing.lg,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.border,
  },
  pkgInfo: {
    gap: 4,
  },
  pkgName: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
  },
  pkgPoints: {
    fontSize: 14,
    color: colors.textSecondary,
  },
  pkgPriceArea: {
    alignItems: 'flex-end',
    gap: 4,
  },
  pkgPrice: {
    fontSize: 18,
    fontWeight: '700',
    color: colors.primary,
  },
  buyText: {
    fontSize: 13,
    color: colors.primary,
    fontWeight: '600',
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
