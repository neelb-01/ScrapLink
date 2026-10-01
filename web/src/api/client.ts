import type { components } from "./schema";

type Schemas = components["schemas"];
export type User = Schemas["UserOut"];
export type Lot = Schemas["LotOut"];
export type Catalogue = Schemas["CatalogueOut"];
export type Material = Schemas["MaterialOut"];
export type Bid = Schemas["BidOut"];
export type Escrow = Schemas["EscrowOut"];
export type CustodyEvent = Schemas["CustodyEventOut"];
export type Certificate = Schemas["CertificateOut"];
export type Verification = Schemas["VerificationOut"];
export type Wallet = Schemas["WalletOut"];
export type RegisterIn = Schemas["RegisterIn"];
export type Grade = "A" | "B" | "C";

const BASE = import.meta.env.VITE_API_BASE ?? "/api";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

let token: string | null = null;
let onUnauthorised: (() => void) | null = null;

export function setToken(value: string | null) {
  token = value;
}

export function setUnauthorisedHandler(handler: () => void) {
  onUnauthorised = handler;
}

type Body = { json?: unknown; form?: FormData };

async function send(method: string, path: string, body: Body = {}): Promise<Response> {
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  let payload: BodyInit | undefined;
  if (body.json !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body.json);
  } else if (body.form) {
    payload = body.form;
  }

  let response: Response;
  try {
    response = await fetch(BASE + path, { method, headers, body: payload });
  } catch {
    throw new ApiError(0, "No connection. Check your internet and try again.");
  }
  if (response.status === 401 && token) onUnauthorised?.();
  if (!response.ok) throw new ApiError(response.status, await errorMessage(response));
  return response;
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const data = await response.json();
    if (typeof data.detail === "string") return capitalise(data.detail);
    // FastAPI validation errors: a list of {loc, msg}.
    if (Array.isArray(data.detail) && data.detail[0]?.msg) return capitalise(data.detail[0].msg);
  } catch {
    // fall through
  }
  return `Something went wrong (${response.status}). Try again.`;
}

function capitalise(text: string) {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

const get = async <T>(path: string) => (await send("GET", path)).json() as Promise<T>;
const post = async <T>(path: string, json?: unknown) =>
  (await send("POST", path, { json: json ?? {} })).json() as Promise<T>;
const postForm = async <T>(path: string, form: FormData) =>
  (await send("POST", path, { form })).json() as Promise<T>;
const put = async <T>(path: string, json: unknown) =>
  (await send("PUT", path, { json })).json() as Promise<T>;

/** For images and PDFs: the API needs the bearer token, which <img src> cannot send. */
export async function fetchBlob(path: string): Promise<Blob> {
  return (await send("GET", path)).blob();
}

export const api = {
  login: (phone: string, password: string) =>
    post<{ access_token: string; user: User }>("/auth/login", { phone, password }),
  register: (body: RegisterIn) => post<User>("/auth/register", body),
  me: () => get<User>("/auth/me"),

  catalogue: () => get<Catalogue>("/materials"),

  lots: (scope: "mine" | "market") => get<Lot[]>(`/lots?scope=${scope}`),
  lot: (id: string) => get<Lot>(`/lots/${id}`),
  createLot: (photo: File) => {
    const form = new FormData();
    form.append("photo", photo);
    return postForm<Lot>("/lots", form);
  },
  confirmLot: (id: string, material_code: string, grade: Grade, declared_weight_grams: number) =>
    post<Lot>(`/lots/${id}/confirm`, { material_code, grade, declared_weight_grams }),
  listLot: (id: string, auction_hours: number, reserve_rate_paise_per_kg: number | null) =>
    post<Lot>(`/lots/${id}/list`, { auction_hours, reserve_rate_paise_per_kg }),
  bid: (id: string, rate_paise_per_kg: number) =>
    post<Lot>(`/lots/${id}/bids`, { rate_paise_per_kg }),
  bids: (id: string) => get<Bid[]>(`/lots/${id}/bids`),
  custody: (id: string) => get<CustodyEvent[]>(`/lots/${id}/custody`),

  declineAward: (id: string) => post<Lot>(`/lots/${id}/decline`),
  startEscrow: (id: string) => post<Escrow>(`/lots/${id}/escrow`),
  simulateCapture: (intentId: string) => post<Escrow>(`/payments/${intentId}/simulate-capture`),
  razorpayVerify: (result: {
    razorpay_order_id: string;
    razorpay_payment_id: string;
    razorpay_signature: string;
  }) => post<Escrow>("/payments/razorpay/verify", result),

  schedulePickup: (id: string, pickupAt: Date) =>
    post<Lot>(`/lots/${id}/pickup`, { pickup_at: pickupAt.toISOString() }),
  recordDelivery: (id: string, measuredGrams: number, slip: File) => {
    const form = new FormData();
    form.append("measured_weight_grams", String(measuredGrams));
    form.append("slip", slip);
    return postForm<Lot>(`/lots/${id}/delivery`, form);
  },
  acceptDelivery: (id: string) => post<Lot>(`/lots/${id}/delivery/accept`),
  disputeDelivery: (id: string, reason: string) =>
    post<Lot>(`/lots/${id}/delivery/dispute`, { reason }),

  certificate: (id: string) => get<Certificate>(`/certificates/${id}`),
  verify: (id: string) => get<Verification>(`/certificates/${id}/verify`),
  wallet: () => get<Wallet>("/wallet"),

  users: (kycStatus?: string) =>
    get<User[]>(`/admin/users${kycStatus ? `?kyc_status=${kycStatus}` : ""}`),
  decideKyc: (userId: string, decision: "approve" | "reject", note?: string) =>
    post<User>(`/admin/users/${userId}/kyc`, { decision, note: note || null }),
  setRate: (code: string, rate_paise_per_kg: number) =>
    put<Material>(`/admin/materials/${code}/rate`, { rate_paise_per_kg }),
};
