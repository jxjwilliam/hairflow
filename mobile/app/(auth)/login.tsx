import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from 'react-native';
import { useRouter } from 'expo-router';
import { colors, spacing, radii } from '../../constants/theme';
import { sendSmsCode, loginWithSms } from '../../services/auth';

export default function LoginScreen() {
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [codeSent, setCodeSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const router = useRouter();

  const handleSendCode = async () => {
    if (phone.length < 5) {
      setError('请输入正确的手机号');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await sendSmsCode(phone);
      setCodeSent(true);
    } catch {
      setError('发送验证码失败，请确认后端已启动');
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async () => {
    if (!code.trim()) {
      setError('请输入验证码');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await loginWithSms(phone, code.trim());
      router.back();
    } catch {
      setError('登录失败，请检查验证码');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <View style={styles.card}>
        <Text style={styles.title}>发型试戴</Text>
        <Text style={styles.subtitle}>登录以保存试戴记录</Text>

        <TextInput
          style={styles.input}
          placeholder="手机号"
          placeholderTextColor={colors.textMuted}
          keyboardType="phone-pad"
          maxLength={11}
          value={phone}
          onChangeText={setPhone}
          accessibilityLabel="手机号输入"
        />

        {codeSent && (
          <TextInput
            style={styles.input}
            placeholder="验证码"
            placeholderTextColor={colors.textMuted}
            keyboardType="number-pad"
            maxLength={6}
            value={code}
            onChangeText={setCode}
            accessibilityLabel="验证码输入"
          />
        )}

        {error ? <Text style={styles.error}>{error}</Text> : null}

        {!codeSent ? (
          <TouchableOpacity
            style={[styles.btn, loading && styles.btnDisabled]}
            onPress={handleSendCode}
            disabled={loading}
            accessibilityRole="button"
            accessibilityLabel="获取验证码"
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.btnText}>获取验证码</Text>
            )}
          </TouchableOpacity>
        ) : (
          <TouchableOpacity
            style={[styles.btn, loading && styles.btnDisabled]}
            onPress={handleLogin}
            disabled={loading}
            accessibilityRole="button"
            accessibilityLabel="登录"
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.btnText}>登录</Text>
            )}
          </TouchableOpacity>
        )}

        <TouchableOpacity
          style={styles.skipBtn}
          onPress={() => router.back()}
          accessibilityRole="button"
          accessibilityLabel="跳过登录"
        >
          <Text style={styles.skipText}>跳过，先浏览</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.xl,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radii.lg,
    padding: spacing.xl,
    width: '100%',
    maxWidth: 380,
    gap: spacing.md,
    alignItems: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: colors.text,
  },
  subtitle: {
    fontSize: 14,
    color: colors.textSecondary,
    marginBottom: spacing.sm,
  },
  input: {
    width: '100%',
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radii.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: 12,
    fontSize: 16,
    color: colors.text,
    backgroundColor: colors.bg,
  },
  btn: {
    width: '100%',
    backgroundColor: colors.primary,
    paddingVertical: 14,
    borderRadius: radii.sm,
    alignItems: 'center',
  },
  btnDisabled: {
    opacity: 0.6,
  },
  btnText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  error: {
    color: colors.danger,
    fontSize: 13,
    textAlign: 'center',
  },
  skipBtn: {
    paddingVertical: spacing.sm,
  },
  skipText: {
    color: colors.textSecondary,
    fontSize: 14,
  },
});
