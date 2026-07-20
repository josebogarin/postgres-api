import { View, Text, StyleSheet } from "react-native";
import { useAuth } from "@/context/AuthContext";

export default function HomeScreen() {
  const { user } = useAuth();

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Bienvenido</Text>
      <Text style={styles.subtitle}>{user?.full_name ?? user?.email}</Text>
      {/* Agrega tus componentes aquí */}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, backgroundColor: "#fff" },
  title:     { fontSize: 24, fontWeight: "700", marginTop: 40, marginBottom: 8 },
  subtitle:  { fontSize: 15, color: "#555" },
});
