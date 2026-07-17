import React, { useState } from 'react';
import {
  View,
  TouchableOpacity,
  Text,
  StyleSheet,
  Alert,
  Platform,
} from 'react-native';
import { colors, radii, spacing } from '../constants/theme';

interface ActionItem {
  label: string;
  onPress: () => void;
  disabled?: boolean;
}

interface Props {
  imageUrl: string;
  onRetry?: () => void;
  onTryAnotherStyle?: () => void;
  onBackHome?: () => void;
  onRetakePhoto?: () => void;
  extraActions?: ActionItem[];
}

function filenameFromUrl(url: string): string {
  try {
    const path = new URL(url, 'http://localhost').pathname;
    const base = path.split('/').pop();
    if (base && /\.(png|jpe?g|webp)$/i.test(base)) return base;
  } catch {
    // ignore
  }
  return `hairstyle-${Date.now()}.png`;
}

/** Same-origin-safe download: cross-origin `a[download]` navigates away (8081 → 8000). */
async function downloadViaBlob(url: string, filename: string): Promise<void> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`下载失败 (${res.status})`);
  }
  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  try {
    const a = document.createElement('a');
    a.href = objectUrl;
    a.download = filename;
    a.rel = 'noopener';
    document.body.appendChild(a);
    a.click();
    a.remove();
  } finally {
    // Revoke after the browser has a chance to start the download
    setTimeout(() => URL.revokeObjectURL(objectUrl), 2_000);
  }
}

async function saveImage(url: string) {
  if (Platform.OS === 'web') {
    await downloadViaBlob(url, filenameFromUrl(url));
    Alert.alert('已保存', '效果图已开始下载到本地');
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
    const filename = filenameFromUrl(url);
    // Prefer Web Share with a File (keeps user on 8081); fall back to copy link.
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`fetch ${res.status}`);
      const blob = await res.blob();
      const file = new File([blob], filename, { type: blob.type || 'image/png' });
      if (typeof navigator !== 'undefined' && navigator.share && navigator.canShare?.({ files: [file] })) {
        await navigator.share({
          title: 'AI 发型效果图',
          text: '我的发型试戴效果',
          files: [file],
        });
        return;
      }
    } catch {
      // fall through to clipboard
    }

    if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(url);
      Alert.alert('链接已复制', '分享链接已复制到剪贴板（可粘贴给好友）');
      return;
    }

    // Last resort: open image in a new tab (does not leave the app tab)
    window.open(url, '_blank', 'noopener,noreferrer');
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
  extraActions,
}: Props) {
  const [busy, setBusy] = useState<'save' | 'share' | null>(null);

  const handleSave = async () => {
    if (busy) return;
    setBusy('save');
    try {
      await saveImage(imageUrl);
    } catch {
      Alert.alert('保存失败', '请稍后重试（确认后端仍在运行）');
    } finally {
      setBusy(null);
    }
  };

  const handleShare = async () => {
    if (busy) return;
    setBusy('share');
    try {
      await shareImage(imageUrl);
    } catch {
      // user cancelled share sheet — ignore
    } finally {
      setBusy(null);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.sectionHint}>效果不错？保存或分享；也可以换发型继续试</Text>
      <View style={styles.row}>
        <TouchableOpacity
          style={[styles.btnPrimary, busy === 'save' && styles.btnDisabled]}
          onPress={handleSave}
          disabled={busy !== null}
          accessibilityRole="button"
          accessibilityLabel="保存效果图"
        >
          <Text style={styles.btnTextLight}>{busy === 'save' ? '保存中…' : '保存'}</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.btnSuccess, busy === 'share' && styles.btnDisabled]}
          onPress={handleShare}
          disabled={busy !== null}
          accessibilityRole="button"
          accessibilityLabel="分享效果图"
        >
          <Text style={styles.btnTextLight}>{busy === 'share' ? '分享中…' : '分享'}</Text>
        </TouchableOpacity>
        {onRetry && (
          <TouchableOpacity
            style={styles.btnGhost}
            onPress={onRetry}
            accessibilityRole="button"
            accessibilityLabel="重新生成"
          >
            <Text style={styles.btnTextPrimary}>重试</Text>
          </TouchableOpacity>
        )}
      </View>

      {extraActions && extraActions.length > 0 && (
        <View style={styles.row}>
          {extraActions.map((action, idx) => (
            <TouchableOpacity
              key={idx}
              style={[styles.btnGhost, action.disabled && styles.btnDisabled]}
              onPress={action.onPress}
              disabled={action.disabled}
              accessibilityRole="button"
              accessibilityLabel={action.label}
            >
              <Text style={styles.btnTextPrimary}>{action.label}</Text>
            </TouchableOpacity>
          ))}
        </View>
      )}

      <View style={styles.row}>
        {onTryAnotherStyle && (
          <TouchableOpacity
            style={styles.btnWide}
            onPress={onTryAnotherStyle}
            accessibilityRole="button"
            accessibilityLabel="换个发型，保留当前照片"
          >
            <Text style={styles.btnTextLight}>换个发型（保留照片）</Text>
          </TouchableOpacity>
        )}
      </View>

      <View style={styles.row}>
        {onRetakePhoto && (
          <TouchableOpacity
            style={styles.btnGhostWide}
            onPress={onRetakePhoto}
            accessibilityRole="button"
            accessibilityLabel="重新拍照"
          >
            <Text style={styles.btnTextPrimary}>重新拍照</Text>
          </TouchableOpacity>
        )}
        {onBackHome && (
          <TouchableOpacity
            style={styles.btnGhostWide}
            onPress={onBackHome}
            accessibilityRole="button"
            accessibilityLabel="返回发型库"
          >
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
  sectionHint: {
    textAlign: 'center',
    fontSize: 13,
    color: colors.textSecondary,
    marginBottom: spacing.xs,
    lineHeight: 18,
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
  btnDisabled: { opacity: 0.65 },
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
