import React from 'react';
import {
  View,
  TouchableOpacity,
  Text,
  StyleSheet,
  Alert,
  Platform,
} from 'react-native';
import { colors, radii, spacing } from '../constants/theme';

interface Props {
  imageUrl: string;
  onRetry?: () => void;
  onTryAnotherStyle?: () => void;
  onBackHome?: () => void;
  onRetakePhoto?: () => void;
}

async function saveImage(url: string) {
  if (Platform.OS === 'web') {
    const a = document.createElement('a');
    a.href = url;
    a.download = 'hairstyle-result.png';
    a.click();
    return;
  }

  const { requestPermissionsAsync, saveToLibraryAsync } = await import('expo-media-library');
  const { status } = await requestPermissionsAsync();
  if (status !== 'granted') {
    Alert.alert('需要权限', '请在设置中允许保存到相册');
    return;
  }
  await saveToLibraryAsync(url);
  Alert.alert('已保存', '效果图已保存到相册');
}

async function shareImage(url: string) {
  if (Platform.OS === 'web') {
    if (typeof navigator !== 'undefined' && navigator.share) {
      await navigator.share({ title: 'AI 发型效果图', url });
    } else {
      await navigator.clipboard.writeText(url);
      Alert.alert('链接已复制', '分享链接已复制到剪贴板');
    }
    return;
  }

  const { shareAsync } = await import('expo-sharing');
  await shareAsync(url);
}

export default function ActionButtons({
  imageUrl,
  onRetry,
  onTryAnotherStyle,
  onBackHome,
  onRetakePhoto,
}: Props) {
  const handleSave = async () => {
    try {
      await saveImage(imageUrl);
    } catch {
      Alert.alert('保存失败', '请稍后重试');
    }
  };

  const handleShare = async () => {
    try {
      await shareImage(imageUrl);
    } catch {
      // user cancelled
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.row}>
        <TouchableOpacity style={styles.btnPrimary} onPress={handleSave}>
          <Text style={styles.btnTextLight}>保存</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.btnSuccess} onPress={handleShare}>
          <Text style={styles.btnTextLight}>分享</Text>
        </TouchableOpacity>
        {onRetry && (
          <TouchableOpacity style={styles.btnGhost} onPress={onRetry}>
            <Text style={styles.btnTextPrimary}>重试</Text>
          </TouchableOpacity>
        )}
      </View>

      <View style={styles.row}>
        {onTryAnotherStyle && (
          <TouchableOpacity style={styles.btnWide} onPress={onTryAnotherStyle}>
            <Text style={styles.btnTextLight}>换个发型（保留照片）</Text>
          </TouchableOpacity>
        )}
      </View>

      <View style={styles.row}>
        {onRetakePhoto && (
          <TouchableOpacity style={styles.btnGhostWide} onPress={onRetakePhoto}>
            <Text style={styles.btnTextPrimary}>重新拍照</Text>
          </TouchableOpacity>
        )}
        {onBackHome && (
          <TouchableOpacity style={styles.btnGhostWide} onPress={onBackHome}>
            <Text style={styles.btnTextPrimary}>返回发型库</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    width: '100%',
    maxWidth: 520,
    alignSelf: 'center',
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.xl,
    gap: spacing.sm,
  },
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: spacing.sm,
  },
  btnPrimary: {
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: radii.sm,
    backgroundColor: colors.primary,
  },
  btnSuccess: {
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: radii.sm,
    backgroundColor: colors.success,
  },
  btnGhost: {
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: radii.sm,
    borderWidth: 1.5,
    borderColor: colors.primary,
    backgroundColor: colors.surface,
  },
  btnWide: {
    flexGrow: 1,
    alignItems: 'center',
    paddingVertical: 13,
    borderRadius: radii.sm,
    backgroundColor: colors.primary,
  },
  btnGhostWide: {
    flexGrow: 1,
    alignItems: 'center',
    paddingVertical: 12,
    borderRadius: radii.sm,
    borderWidth: 1.5,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  btnTextLight: { color: '#fff', fontSize: 15, fontWeight: '600' },
  btnTextPrimary: { color: colors.primary, fontSize: 15, fontWeight: '600' },
});
