import AsyncStorage from "@react-native-async-storage/async-storage";

// The API the app talks to. On a phone, localhost is the phone itself: set
// EXPO_PUBLIC_API_URL=http://<your computer's LAN address>:8000 before `npm start`.
export const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

export type User = { id: string; name: string; role: string; business_name: string | null };

export type Lot = {
  id: string;
  status: string;
  material_code: string | null;
  material_name: string | null;
  grade: string | null;
  declared_weight_grams: number | null;
  measured_weight_grams: number | null;
  settled_amount_paise: number | null;
};

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  let response: Response;
  try {
    response = await fetch(API_URL + path, { ...init, headers });
  } catch {
    throw new ApiError(0, "No connection");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(response.status, typeof body.detail === "string" ? body.detail : `Error ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const signIn = (phone: string, password: string) =>
  request<{ access_token: string; user: User }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ phone, password }),
  });

export const myLots = (token: string) => request<Lot[]>("/lots?scope=mine", {}, token);

// --- Offline-first, first slice: the last lots seen are kept on the phone, so the list still
// opens with no signal. Writing (listing a lot, booking a pickup) offline comes next.

const SESSION = "scraplink.session";
const LOTS = "scraplink.lots";

export type Session = { token: string; user: User };
export type SavedLots = { lots: Lot[]; savedAt: string };

export async function loadSession(): Promise<Session | null> {
  const raw = await AsyncStorage.getItem(SESSION);
  return raw ? (JSON.parse(raw) as Session) : null;
}

export const saveSession = (session: Session) => AsyncStorage.setItem(SESSION, JSON.stringify(session));

export const clearSession = () => AsyncStorage.multiRemove([SESSION, LOTS]);

export async function loadSavedLots(): Promise<SavedLots | null> {
  const raw = await AsyncStorage.getItem(LOTS);
  return raw ? (JSON.parse(raw) as SavedLots) : null;
}

export const saveLots = (lots: Lot[]) =>
  AsyncStorage.setItem(LOTS, JSON.stringify({ lots, savedAt: new Date().toISOString() }));
