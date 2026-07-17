import { Tabs } from 'expo-router';
import { Platform, Text, View } from 'react-native';
import { colors } from '../../constants/theme';
import AppLogo from '../../components/AppLogo';

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: true,
        headerStyle: { backgroundColor: colors.surface },
        headerShadowVisible: true,
        headerTitleAlign: 'left',
        headerTitle: () => (
          <View style={{ paddingVertical: 4, paddingRight: 12 }}>
            <AppLogo compact subtitle="选发型 · 上传照片 · 看效果" />
          </View>
        ),
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarLabelStyle: { fontSize: 12, fontWeight: '600' },
        tabBarStyle: {
          backgroundColor: colors.surface,
          borderTopColor: colors.border,
          height: Platform.OS === 'web' ? 56 : undefined,
          paddingTop: Platform.OS === 'web' ? 6 : undefined,
        },
        // Avoid custom icon nodes — Expo web often doubles them in the a11y tree
        tabBarIcon: () => null,
        tabBarIconStyle: { display: 'none', width: 0, height: 0 },
        lazy: true,
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: '发型库',
          href: '/',
          tabBarLabel: '发型',
          tabBarAccessibilityLabel: '发型库',
        }}
      />
      <Tabs.Screen
        name="history"
        options={{
          title: '我的效果',
          href: '/history',
          tabBarLabel: '效果',
          tabBarAccessibilityLabel: '我的效果',
        }}
      />
    </Tabs>
  );
}
