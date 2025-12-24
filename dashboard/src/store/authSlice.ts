import { create } from "zustand";
import type { UserSummary } from "../client/models";
import { setAuthToken, getAuthToken as getAxiosToken } from "../lib/setupAxios";
import { AUTH_STORAGE_KEY } from "../features/auth/constants";

type StoredAuth = {
  token: string;
  user: UserSummary;
};

interface AuthState {
  token?: string;
  user?: UserSummary;
  initialized: boolean;
  hydrate: () => void;
  login: (token: string, user: UserSummary) => void;
  updateUser: (user: UserSummary) => void;
  logout: () => void;
  hasRole: (roles: string | string[]) => boolean;
}

const loadStoredAuth = (): StoredAuth | null => {
  try {
    const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    return JSON.parse(raw) as StoredAuth;
  } catch {
    return null;
  }
};

export const useAuthStore = create<AuthState>((set, get) => ({
  token: undefined,
  user: undefined,
  initialized: false,
  hydrate: () => {
    const stored = loadStoredAuth();
    if (stored?.token) {
      setAuthToken(stored.token);
      set({ token: stored.token, user: stored.user, initialized: true });
    } else {
      const fallback = getAxiosToken();
      if (fallback) {
        set({ token: fallback, initialized: true });
      } else {
        set({ initialized: true });
      }
    }
  },
  login: (token, user) => {
    window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify({ token, user }));
    setAuthToken(token);
    set({ token, user, initialized: true });
  },
  updateUser: (user) => {
    const token = get().token ?? getAxiosToken();
    if (token) {
      window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify({ token, user }));
    }
    set({ user });
  },
  logout: () => {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
    setAuthToken(undefined);
    set({ token: undefined, user: undefined, initialized: true });
  },
  hasRole: (roles) => {
    const targetRoles = Array.isArray(roles) ? roles : [roles];
    const assigned = get().user?.roles ?? [];
    return targetRoles.some((role) => assigned.includes(role));
  },
}));
