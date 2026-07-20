import { useState } from "react";
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert } from "react-native";
import { useAuth } from "@/context/AuthContext";

export default function LoginScreen() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!email || !password) { Alert.alert("Error", "Ingresa email y contraseña"); return; }
    setLoading(true);
    try {
      await login(email, password);
    } catch (e: unknown) {
      Alert.alert("Error", e instanceof Error ? e.message : "Error al iniciar sesión");
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>TEMPLATE_TITLE</Text>
      <TextInput
        style={styles.input}
        placeholder="Email"
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        keyboardType="email-address"
      />
      <TextInput
        style={styles.input}
        placeholder="Contraseña"
        value={password}
        onChangeText={setPassword}
        secureTextEntry
      />
      <TouchableOpacity style={styles.btn} onPress={handleLogin} disabled={loading}>
        <Text style={styles.btnText}>{loading ? "Iniciando..." : "Ingresar"}</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", padding: 24, backgroundColor: "#fff" },
  title:     { fontSize: 26, fontWeight: "700", textAlign: "center", marginBottom: 32 },
  input:     { borderWidth: 1, borderColor: "#ddd", borderRadius: 8, padding: 12, marginBottom: 12, fontSize: 15 },
  btn:       { backgroundColor: "#2563eb", borderRadius: 8, padding: 14, alignItems: "center" },
  btnText:   { color: "#fff", fontWeight: "600", fontSize: 16 },
});
