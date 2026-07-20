import { View, Text, TouchableOpacity, StyleSheet, Alert } from "react-native";
import { useAuth } from "@/context/AuthContext";

export default function PerfilScreen() {
  const { user, logout } = useAuth();

  const handleLogout = () => {
    Alert.alert("Cerrar sesión", "¿Deseas salir?", [
      { text: "Cancelar", style: "cancel" },
      { text: "Salir", style: "destructive", onPress: logout },
    ]);
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Mi Perfil</Text>

      <View style={styles.card}>
        <Row label="Nombre" value={user?.full_name ?? "—"} />
        <Row label="Email"  value={user?.email ?? "—"} />
        <Row label="Rol"    value={user?.is_superuser ? "Administrador" : "Usuario"} />
      </View>

      <TouchableOpacity style={styles.btnLogout} onPress={handleLogout}>
        <Text style={styles.btnText}>Cerrar sesión</Text>
      </TouchableOpacity>
    </View>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.label}>{label}</Text>
      <Text style={styles.value}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container:  { flex: 1, padding: 24, backgroundColor: "#fff" },
  title:      { fontSize: 24, fontWeight: "700", marginTop: 40, marginBottom: 24 },
  card:       { borderWidth: 1, borderColor: "#e5e7eb", borderRadius: 10, padding: 16, marginBottom: 32, gap: 12 },
  row:        { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  label:      { fontSize: 14, color: "#6b7280", fontWeight: "500" },
  value:      { fontSize: 14, color: "#111827", flexShrink: 1, textAlign: "right" },
  btnLogout:  { backgroundColor: "#ef4444", borderRadius: 8, padding: 14, alignItems: "center" },
  btnText:    { color: "#fff", fontWeight: "600", fontSize: 16 },
});
