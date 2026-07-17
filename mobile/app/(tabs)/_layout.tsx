import { Tabs } from 'expo-router';
import { Text, Platform, View } from 'react-native';
import { colors } from '../../constants/theme';
import AppLogo from '../../components/AppLogo';

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: true,
        headerStyle: { backgroundColor: colors.surface },
        headerTitleStyle: { fontWeight: '700', color: colors.text },
        headerTitle: () => (
          <View style={{ paddingVertical: 4 }}>
            <AppLogo compact subtitle="AI 虚拟试戴" />
          </View>
        ),
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarStyle: {
          backgroundColor: colors.surface,
          borderTopColor: colors.border,
          height: Platform.OS === 'web' ? 56 : undefined,
        },
        tabBarLabelStyle: { fontSize: 12, fontWeight: '600' },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: '发型库',
          tabBarLabel: '发型',
          tabBarIcon: ({ color }) => <Text style={{ fontSize: 18, color }}>✂</Text>,
        }}
      />
      <Tabs.Screen
        name="history"
        options={{
          title: '我的效果',
          tabBarLabel: '效果',
          tabBarIcon: ({ color }) => <Text style={{ fontSize: 18, color }}>▣</Text>,
        }}
      />
    </Tabs>
  );
}
