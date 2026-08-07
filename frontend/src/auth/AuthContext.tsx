import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ApiError,
  accessTokenExpiresSoon,
  clearToken,
  ensureFreshToken,
  fetchMe,
  getToken,
  onTokenChange,
  refreshAccessToken,
  setTokens,
} from "../api/client";
import type { User } from "../types";

interface AuthContextValue {
  user: User | null;
  token: string | null;
  loading: boolean;
  isAuthenticated: boolean;
  loginWithToken: (accessToken: string, refreshToken?: string | null) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [token, setTokenState] = useState<string | null>(() => getToken());

  useEffect(() => onTokenChange(setTokenState), []);

  // Proactively refresh access token while the app is open
  useEffect(() => {
    let cancelled = false;

    async function tick() {
      if (cancelled) return;
      const current = getToken();
      if (!current) return;
      if (accessTokenExpiresSoon(current)) {
        await refreshAccessToken();
      } else {
        await ensureFreshToken();
      }
    }

    void tick();
    const id = window.setInterval(() => void tick(), 60_000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  const meQuery = useQuery({
    queryKey: ["me", token],
    queryFn: fetchMe,
    enabled: Boolean(token),
    retry: false,
  });

  useEffect(() => {
    if (meQuery.error instanceof ApiError && meQuery.error.status === 401) {
      clearToken();
      setTokenState(null);
    }
  }, [meQuery.error]);

  const loginWithToken = useCallback(
    (accessToken: string, refreshToken?: string | null) => {
      setTokens(accessToken, refreshToken);
      setTokenState(accessToken);
      void queryClient.invalidateQueries({ queryKey: ["me"] });
    },
    [queryClient],
  );

  const logout = useCallback(() => {
    clearToken();
    setTokenState(null);
    queryClient.clear();
  }, [queryClient]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user: meQuery.data ?? null,
      token,
      loading: Boolean(token) && meQuery.isLoading,
      isAuthenticated: Boolean(token && meQuery.data),
      loginWithToken,
      logout,
    }),
    [meQuery.data, meQuery.isLoading, token, loginWithToken, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
