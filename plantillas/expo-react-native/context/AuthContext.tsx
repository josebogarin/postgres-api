import React, { createContext, useContext, useEffect, useState } from "react";
import { api, tokenStorage } from "@/services/api";

const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Restaurar sesión al arrancar
  useEffect(() => {
    (async () => {
      try {
        const token = await tokenStorage.getAccess();
        if (token) {
          const me = await api.get<User>("/auth/me");
          setUser(me);
        }
      } catch {
        await tokenStorage.clear();
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const login = async (email: string, password: string) => {
    const res = await fetch(`${BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err?.detail ?? "Credenciales inválidas");
    }
    const data = await res.json();
    await tokenStorage.set(data.access_token, data.refresh_token);
    const me = await api.get<User>("/auth/me");
    setUser(me);
  };

  const logout = async () => {
    await tokenStorage.clear();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de AuthProvider");
  return ctx;
}
