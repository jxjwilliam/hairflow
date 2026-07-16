import { Tabs } from 'expo-router';
import { Text } from 'react-native';

export default function TabLayout() {
  return (
    <Tabs screenOptions={{ headerShown: false }}>
      <Tabs.Screen
        name="index"
        options={{
          title: '发型',
          tabBarIcon: () => <Text>💇</Text>,
        }}
      />
    </Tabs>
  );
}
