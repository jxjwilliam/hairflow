import React from 'react';
import {
  View,
  TouchableOpacity,
  Text,
  Image,
  StyleSheet,
  Platform,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { colors, radii, spacing, THUMB_ASPECT } from '../constants/theme';
import { useLayout } from '../hooks/useLayout';

interface Props {
  photoUri: string | null;
  onPhotoTaken: (base64: string, uri: string) => void;
  templateName?: string;
  onBack?: () => void;
}

export default function PhotoCapture({
  photoUri,
  onPhotoTaken,
  templateName,
  onBack,
}: Props) {
  const { mode } = useLayout();
  const boxW = mode === 'phone' ? 260 : 300;
  const boxH = boxW / THUMB_ASPECT;

  const takePhoto = async () => {
    if (Platform.OS === 'web') {
      // Camera often unavailable on web — fall through to picker UX
      await pickPhoto();
      return;
    }
    const result = await ImagePicker.launchCameraAsync({
      base64: true,
      quality: 0.8,
    });
    if (!result.canceled && result.assets[0]) {
      onPhotoTaken(result.assets[0].base64 || '', result.assets[0].uri);
    }
  };

  const pickPhoto = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      base64: true,
      quality: 0.8,
    });
    if (!result.canceled && result.assets[0]) {
      onPhotoTaken(result.assets[0].base64 || '', result.assets[0].uri);
    }
  };

  return (
    <View style={styles.container}>
      {onBack && (
        <TouchableOpacity
          style={styles.back}
          onPress={onBack}
          accessibilityRole="button"
          accessibilityLabel="返回发型库"
        >
          <Text style={styles.backText}>← 返回发型库</Text>
        </TouchableOpacity>
      )}

      <Text style={styles.title}>上传正面头像</Text>
      {templateName ? (
        <Text style={styles.subtitle}>将试戴：{templateName}</Text>
      ) : (
        <Text style={styles.subtitle}>请使用清晰正面照，光线均匀，头发轮廓可见</Text>
      )}
      <Text style={styles.stepHint}>步骤 2 / 3 · 选好照片后自动进入生成</Text>

      {photoUri ? (
        <Image source={{ uri: photoUri }} style={[styles.preview, { width: boxW, height: boxH }]} />
      ) : (
        <View style={[styles.placeholder, { width: boxW, height: boxH }]}>
          <Text style={styles.placeholderText}>正面 · 肩部以上</Text>
        </View>
      )}

      <View style={styles.buttons}>
        {Platform.OS !== 'web' && (
          <TouchableOpacity style={styles.btn} onPress={takePhoto}>
            <Text style={styles.btnText}>拍照</Text>
          </TouchableOpacity>
        )}
        <TouchableOpacity
          style={[styles.btn, styles.btnOutline, Platform.OS === 'web' && styles.btnWebPrimary]}
          onPress={pickPhoto}
          accessibilityRole="button"
          accessibilityLabel="从相册选择照片"
        >
          <Text
            style={[
              styles.btnText,
              styles.btnTextOutline,
              Platform.OS === 'web' && styles.btnTextLight,
            ]}
          >
            从相册选择
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.xl,
    backgroundColor: colors.bg,
  },
  back: {
    position: 'absolute',
    top: spacing.lg,
    left: spacing.lg,
    padding: spacing.sm,
  },
  backText: { fontSize: 16, color: colors.primary, fontWeight: '600' },
  title: { fontSize: 22, fontWeight: '700', color: colors.text, marginBottom: 6 },
  subtitle: {
    fontSize: 14,
    color: colors.textSecondary,
    marginBottom: spacing.sm,
    textAlign: 'center',
    maxWidth: 320,
  },
  stepHint: {
    fontSize: 12,
    color: colors.textMuted,
    marginBottom: spacing.xl,
  },
  preview: { borderRadius: radii.lg, marginBottom: spacing.xl },
  placeholder: {
    borderRadius: radii.lg,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderStyle: 'dashed',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.xl,
  },
  placeholderText: { color: colors.textMuted, fontSize: 15 },
  buttons: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md, justifyContent: 'center' },
  btn: {
    paddingHorizontal: 28,
    paddingVertical: 14,
    borderRadius: radii.md,
    backgroundColor: colors.primary,
  },
  btnOutline: {
    backgroundColor: colors.surface,
    borderWidth: 1.5,
    borderColor: colors.primary,
  },
  btnWebPrimary: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  btnText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  btnTextOutline: { color: colors.primary },
  btnTextLight: { color: '#fff' },
});
