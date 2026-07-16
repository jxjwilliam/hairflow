import React from 'react';
import { View, TouchableOpacity, Text, Image, StyleSheet } from 'react-native';
import * as ImagePicker from 'expo-image-picker';

interface Props {
  photoUri: string | null;
  onPhotoTaken: (base64: string, uri: string) => void;
}

export default function PhotoCapture({ photoUri, onPhotoTaken }: Props) {
  const takePhoto = async () => {
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
      {photoUri ? (
        <Image source={{ uri: photoUri }} style={styles.preview} />
      ) : (
        <View style={styles.placeholder}>
          <Text style={styles.placeholderText}>上传正面头像照片</Text>
        </View>
      )}
      <View style={styles.buttons}>
        <TouchableOpacity style={styles.btn} onPress={takePhoto}>
          <Text style={styles.btnText}>📸 拍照</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.btn, styles.btnOutline]}
          onPress={pickPhoto}
        >
          <Text style={[styles.btnText, styles.btnTextOutline]}>🖼️ 相册</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  preview: { width: 300, height: 400, borderRadius: 16, marginBottom: 24 },
  placeholder: {
    width: 300,
    height: 400,
    borderRadius: 16,
    backgroundColor: '#e5e7eb',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 24,
  },
  placeholderText: { color: '#999', fontSize: 16 },
  buttons: { flexDirection: 'row', gap: 16 },
  btn: { paddingHorizontal: 32, paddingVertical: 14, borderRadius: 12, backgroundColor: '#2563eb' },
  btnOutline: { backgroundColor: 'transparent', borderWidth: 2, borderColor: '#2563eb' },
  btnText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  btnTextOutline: { color: '#2563eb' },
});
