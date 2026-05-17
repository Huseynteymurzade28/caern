import { create } from "zustand";
import { persist } from "zustand/middleware";
import { jwtDecode } from "jwt-decode";
import type { User, UserRole } from "@/types";

interface TokenPayload {
  sub: string;
  email: string;
  role: UserRole;
  exp: number;
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: Partial<User> | null;
  setTokens: (access: string, refresh: string) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: null,

      setTokens: (access, refresh) => {
        const payload = jwtDecode<TokenPayload>(access);
        localStorage.setItem("access_token", access);
        localStorage.setItem("refresh_token", refresh);
        set({
          accessToken: access,
          refreshToken: refresh,
          user: { id: payload.sub, email: payload.email, role: payload.role },
        });
      },

      logout: () => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        set({ accessToken: null, refreshToken: null, user: null });
      },

      isAuthenticated: () => {
        const token = get().accessToken;
        if (!token) return false;
        try {
          const { exp } = jwtDecode<TokenPayload>(token);
          return Date.now() / 1000 < exp;
        } catch {
          return false;
        }
      },
    }),
    { name: "caern-auth" }
  )
);
