import React, { createContext, useContext, useEffect, useState } from "react";
import { User, UserRole } from "../types";
import { api } from "../api/client";

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (email: string, pass: string) => Promise<void>;
  logout: () => void;
  quickSwitchRole: (role: UserRole) => Promise<void>;
  hasRole: (allowedRoles: UserRole[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const DEMO_CREDENTIALS: Record<UserRole, { email: string; pass: string; title: string }> = {
  admin: { email: "admin@sutra.ai", pass: "admin123", title: "Chief AI Officer (Admin)" },
  compliance_officer: { email: "compliance@sutra.ai", pass: "compliance123", title: "Compliance Officer" },
  engineer: { email: "engineer@sutra.ai", pass: "engineer123", title: "Lead ML Engineer" },
  auditor: { email: "auditor@sutra.ai", pass: "auditor123", title: "External Auditor" },
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem("sutra_user");
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState<string | null>(() => {
    return localStorage.getItem("sutra_token");
  });

  const login = async (email: string, pass: string) => {
    const res = await api.login(email, pass);
    setToken(res.access_token);
    setUser(res.user);
    localStorage.setItem("sutra_token", res.access_token);
    localStorage.setItem("sutra_user", JSON.stringify(res.user));
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("sutra_token");
    localStorage.removeItem("sutra_user");
  };

  const quickSwitchRole = async (role: UserRole) => {
    const creds = DEMO_CREDENTIALS[role];
    if (creds) {
      await login(creds.email, creds.pass);
    }
  };

  const hasRole = (allowedRoles: UserRole[]) => {
    if (!user) return false;
    return allowedRoles.includes(user.role);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, quickSwitchRole, hasRole }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within an AuthProvider");
  return context;
};
