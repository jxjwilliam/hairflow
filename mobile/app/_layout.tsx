import { Stack } from 'expo-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SessionProvider } from '../context/SessionContext';
import { colors } from '../constants/theme';

const queryClient = new QueryClient();

export default function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <SessionProvider>
        <Stack
          screenOptions={{
            headerStyle: { backgroundColor: colors.surface },
            headerTintColor: colors.primary,
            headerTitleStyle: { color: colors.text, fontWeight: '600' },
            contentStyle: { backgroundColor: colors.bg },
          }}
        >
          <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
          <Stack.Screen
            name="capture"
            options={{
              title: '上传照片',
              presentation: 'modal',
              headerShown: true,
            }}
          />
          <Stack.Screen
            name="preview"
            options={{
              title: '试戴效果',
              presentation: 'card',
              headerShown: true,
              headerBackTitle: '返回',
            }}
          />
          <Stack.Screen
            name="result-view"
            options={{
              title: '效果详情',
              presentation: 'card',
              headerShown: true,
              headerBackTitle: '返回',
            }}
          />
        </Stack>
      </SessionProvider>
    </QueryClientProvider>
  );
}
