import axios from 'axios';
import { Platform } from 'react-native';
import Constants from 'expo-constants';
import AsyncStorage from '@react-native-async-storage/async-storage';

const TOKEN_KEY = 'auth_token';

function getBaseUrl(): string {
  if (!__DEV__) {
    return 'https://api.your-domain.com';
  }

  // Web runs in the browser on the dev machine
  if (Platform.OS === 'web') {
    return 'http://localhost:8000';
  }

  // In Expo Go / emulator, expo-constants gives us the dev server host.
  // e.g. "192.168.0.15:8081" (LAN) or "localhost:8081" (simulator/emulator)
  const hostUri = Constants.expoConfig?.hostUri;
  const host = hostUri?.split(':')[0] || 'localhost';

  // Android emulator uses 10.0.2.2 to reach the host machine
  if (Platform.OS === 'android' && host === 'localhost') {
    return 'http://10.0.2.2:8000';
  }

  return `http://${host}:8000`;
}

const api = axios.create({
  baseURL: getBaseUrl(),
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use(async (config) => {
  const token = await AsyncStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
