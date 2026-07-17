import { Stack } from 'expo-router';
import { colors } from '../../constants/theme';

export default function AuthLayout() {
  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: colors.surface },
        headerTintColor: colors.primary,
        headerTitleStyle: { color: colors.text, fontWeight: '600' },
        contentStyle: { backgroundColor: colors.bg },
      }}
    >
      <Stack.Screen name="login" options={{ title: '登录', presentation: 'modal' }} />
    </Stack>
  );
}
