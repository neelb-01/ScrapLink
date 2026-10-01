import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, setToken, setUnauthorisedHandler, type User } from "./api/client";

const STORAGE_KEY = "scraplink.token";

function readStoredToken(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function storeToken(value: string | null) {
  try {
    if (value) localStorage.setItem(STORAGE_KEY, value);
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Private mode: the session simply lasts until the tab closes.
  }
}

type Auth = {
  user: User | null;
  loading: boolean;
  signIn: (phone: string, password: string) => Promise<User>;
  signOut: () => void;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<Auth | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const signOut = useCallback(() => {
    setToken(null);
    storeToken(null);
    setUser(null);
  }, []);

  const refresh = useCallback(async () => {
    setUser(await api.me());
  }, []);

  useEffect(() => {
    setUnauthorisedHandler(signOut);
    const stored = readStoredToken();
    if (!stored) {
      setLoading(false);
      return;
    }
    setToken(stored);
    api
      .me()
      .then(setUser)
      .catch(signOut)
      .finally(() => setLoading(false));
  }, [signOut]);

  const signIn = useCallback(async (phone: string, password: string) => {
    const result = await api.login(phone, password);
    setToken(result.access_token);
    storeToken(result.access_token);
    setUser(result.user);
    return result.user;
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signOut, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): Auth {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error("useAuth outside AuthProvider");
  return auth;
}

/** Signed in and approved: every page behind the shell can rely on this. */
export function useUser(): User {
  const { user } = useAuth();
  if (!user) throw new Error("useUser without a signed-in user");
  return user;
}
