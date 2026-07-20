import { Tabs } from "expo-router";

export default function TabLayout() {
  return (
    <Tabs screenOptions={{ tabBarActiveTintColor: "#2563eb" }}>
      <Tabs.Screen name="index"   options={{ title: "Inicio" }} />
      <Tabs.Screen name="perfil"  options={{ title: "Perfil" }} />
    </Tabs>
  );
}
