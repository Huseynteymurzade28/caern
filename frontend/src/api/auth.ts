import { apiClient } from "./client";
import type { TokenPair } from "@/types";

export const authApi = {
  login: async (email: string, password: string): Promise<TokenPair> => {
    const { data } = await apiClient.post<TokenPair>("/auth/login", { email, password });
    return data;
  },

  refresh: async (refresh_token: string): Promise<TokenPair> => {
    const { data } = await apiClient.post<TokenPair>("/auth/refresh", { refresh_token });
    return data;
  },
};
