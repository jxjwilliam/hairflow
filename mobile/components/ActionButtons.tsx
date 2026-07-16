import React from 'react';
import { View, TouchableOpacity, Text, StyleSheet, Alert } from 'react-native';
import * as MediaLibrary from 'expo-media-library';
import * as Sharing from 'expo-sharing';

interface Props {
  imageUrl: string;
  onRetry?: () => void;
}

export default function ActionButtons({ imageUrl, onRetry }: Props) {
  const handleSave = async () => {
    try {
      const { status } = await MediaLibrary.requestPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('需要权限', '请在设置中允许保存到相册');
        return;
      }
      await MediaLibrary.saveToLibraryAsync(imageUrl);
      Alert.alert('已保存', '效果图已保存到相册');
    } catch {
      Alert.alert('保存失败', '请稍后重试');
    }
  };

  const handleShare = async () => {
    try {
      await Sharing.shareAsync(imageUrl);
    } catch {
      // user cancelled
    }
  };

  return (
    <View style={styles.container}>
      <TouchableOpacity style={styles.btn} onPress={handleSave}>
        <Text style={styles.btnText}>💾 保存</Text>
      </TouchableOpacity>
      <TouchableOpacity style={[styles.btn, styles.btnSecondary]} onPress={handleShare}>
        <Text style={styles.btnText}>📤 分享</Text>
      </TouchableOpacity>
      {onRetry && (
        <TouchableOpacity style={[styles.btn, styles.btnOutline]} onPress={onRetry}>
          <Text style={[styles.btnText, styles.btnTextOutline]}>🔄 重试</Text>
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
