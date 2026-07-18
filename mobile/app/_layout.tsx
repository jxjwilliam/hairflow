import { Stack } from 'expo-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect } from 'react';
import { Platform } from 'react-native';
import { SessionProvider } from '../context/SessionContext';
import { colors } from '../constants/theme';

const queryClient = new QueryClient();

function useDocumentTitle(title: string) {
  useEffect(() => {
    if (Platform.OS === 'web' && typeof document !== 'undefined') {
      document.title = title;
    }
  }, [title]);
}

export default function RootLayout() {
  useDocumentTitle('发型试戴');

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
              headerBackTitle: '发型库',
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
          <Stack.Screen
            name="(auth)"
            options={{ headerShown: false }}
          />
          <Stack.Screen
            name="recharge"
            options={{
              title: '购买点数',
              presentation: 'modal',
              headerShown: true,
            }}
          />
          <Stack.Screen
            name="membership"
            options={{
              title: '会员中心',
              presentation: 'modal',
              headerShown: true,
            }}
          />
        </Stack>
      </SessionProvider>
    </QueryClientProvider>
  );
}
