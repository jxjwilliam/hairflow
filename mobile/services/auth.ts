import AsyncStorage from '@react-native-async-storage/async-storage';
import api from './api';

const TOKEN_KEY = 'auth_token';
const USER_KEY = 'auth_user';

export interface AuthUser {
  user_id: number;
  points_balance: number;
  nickname: string | null;
}

export async function getToken(): Promise<string | null> {
  return AsyncStorage.getItem(TOKEN_KEY);
}

export async function setToken(token: string): Promise<void> {
  await AsyncStorage.setItem(TOKEN_KEY, token);
}

export async function clearToken(): Promise<void> {
  await AsyncStorage.multiRemove([TOKEN_KEY, USER_KEY]);
}

export async function isLoggedIn(): Promise<boolean> {
  const token = await getToken();
  return token !== null;
}

export async function sendSmsCode(phone: string): Promise<void> {
  await api.post('/api/v1/auth/sms/send', { phone });
}

export async function loginWithSms(
  phone: string,
  code: string,
): Promise<{ user: AuthUser; token: string }> {
  const res = await api.post('/api/v1/auth/sms/login', { phone, code });
  const { user_id, token, points_balance, nickname } = res.data;
  await setToken(token);
  const user: AuthUser = { user_id, points_balance, nickname };
  await AsyncStorage.setItem(USER_KEY, JSON.stringify(user));
  return { user, token };
}

export async function getCachedUser(): Promise<AuthUser | null> {
  const raw = await AsyncStorage.getItem(USER_KEY);
  if (!raw) return null;
  return JSON.parse(raw) as AuthUser;
}

export async function fetchProfile(): Promise<AuthUser> {
  const res = await api.get('/api/v1/auth/me');
  const { id, points_balance, nickname } = res.data;
  const user: AuthUser = { user_id: id, points_balance, nickname };
  await AsyncStorage.setItem(USER_KEY, JSON.stringify(user));
  return user;
}
