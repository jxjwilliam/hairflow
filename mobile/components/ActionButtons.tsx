import React from 'react';
import { View, TouchableOpacity, Text, StyleSheet, Alert, Platform } from 'react-native';

interface Props {
  imageUrl: string;
  onRetry?: () => void;
}

async function saveImage(url: string) {
  if (Platform.OS === 'web') {
    // Web: trigger download via anchor click
    const a = document.createElement('a');
    a.href = url;
    a.download = 'hairstyle-result.png';
    a.click();
    return;
  }

  // Native: use expo-media-library
  const { requestPermissionsAsync, saveToLibraryAsync } = await import(
    'expo-media-library'
  );
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
    // Web: use Web Share API if available
    if (typeof navigator !== 'undefined' && navigator.share) {
      await navigator.share({
        title: 'AI 发型效果图',
        url,
      });
    } else {
      // Fallback: copy URL to clipboard
      await navigator.clipboard.writeText(url);
      Alert.alert('链接已复制', '分享链接已复制到剪贴板');
    }
    return;
  }

  // Native: use expo-sharing
  const { shareAsync } = await import('expo-sharing');
  await shareAsync(url);
}

export default function ActionButtons({ imageUrl, onRetry }: Props) {
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
      <TouchableOpacity style={styles.btn} onPress={handleSave}>
        <Text style={styles.btnText}>保存</Text>
      </TouchableOpacity>
      <TouchableOpacity style={[styles.btn, styles.btnSecondary]} onPress={handleShare}>
        <Text style={styles.btnText}>分享</Text>
      </TouchableOpacity>
      {onRetry && (
        <TouchableOpacity style={[styles.btn, styles.btnOutline]} onPress={onRetry}>
          <Text style={[styles.btnText, styles.btnTextOutline]}>重试</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flexDirection: 'row', justifyContent: 'center', gap: 12, paddingVertical: 16 },
  btn: { paddingHorizontal: 24, paddingVertical: 12, borderRadius: 10, backgroundColor: '#2563eb' },
  btnSecondary: { backgroundColor: '#059669' },
  btnOutline: { backgroundColor: 'transparent', borderWidth: 2, borderColor: '#2563eb' },
  btnText: { color: '#fff', fontSize: 15, fontWeight: '600' },
  btnTextOutline: { color: '#2563eb' },
});
