import type { components } from "./schema";

type Schemas = components["schemas"];
export type User = Schemas["UserOut"];
export type Lot = Schemas["LotOut"];
export type Catalogue = Schemas["CatalogueOut"];
export type Material = Schemas["MaterialOut"];
export type Rate = Schemas["RateOut"];
export type Bid = Schemas["BidOut"];
export type Escrow = Schemas["EscrowOut"];
export type CustodyEvent = Schemas["CustodyEventOut"];
export type Certificate = Schemas["CertificateOut"];
export type Verification = Schemas["VerificationOut"];
export type Wallet = Schemas["WalletOut"];
export type RegisterIn = Schemas["RegisterIn"];
export type Party = Schemas["PartyOut"];
export type Rfq = Schemas["RfqOut"];
export type RfqIn = Schemas["RfqIn"];
export type Agreement = Schemas["AgreementOut"];
export type AgreementIn = Schemas["AgreementIn"];
export type Invoice = Schemas["InvoiceOut"];
export type Impact = Schemas["ImpactOut"];
export type Transporter = Schemas["TransporterOut"];
export type TransporterIn = Schemas["TransporterIn"];
export type Route = Schemas["RouteOut"];
export type RouteStop = Schemas["RouteStopOut"];
export type Anchor = Schemas["AnchorOut"];
export type Job = Schemas["JobOut"];
export type JobRun = Schemas["JobRunOut"];
export type Authorisation = "e_waste" | "battery";
export type Dispute = Schemas["DisputeOut"];
export type ResolveIn = Schemas["ResolveIn"];
export type Grade = "A" | "B" | "C";
export type Place = Schemas["PlaceOut"];
export type ProfileIn = Schemas["ProfileIn"];
export type Notifications = Schemas["NotificationsOut"];
export type Notification = Schemas["NotificationOut"];
export type MaterialIn = Schemas["MaterialIn"];
export type Overview = Schemas["OverviewOut"];
export type AuctionFormat = "sealed" | "open";
export type LotDetails = {
  material_code: string;
  grade: Grade;
  declared_weight_grams: number;
  place: string | null;
  pickup_ready_on: string | null;
};
export type MarketFilter = { family?: string; place?: string };

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
const patch = async <T>(path: string, json: unknown) =>
  (await send("PATCH", path, { json })).json() as Promise<T>;

/** For images and PDFs: the API needs the bearer token, which <img src> cannot send. */
export async function fetchBlob(path: string): Promise<Blob> {
  return (await send("GET", path)).blob();
}

export const api = {
  login: (phone: string, password: string) =>
    post<{ access_token: string; user: User }>("/auth/login", { phone, password }),
  register: (body: RegisterIn) => post<User>("/auth/register", body),
  me: () => get<User>("/auth/me"),
  updateProfile: (body: ProfileIn) => patch<User>("/auth/me", body),
  uploadKycDocument: (document: File) => {
    const form = new FormData();
    form.append("document", document);
    return postForm<User>("/auth/me/kyc-document", form);
  },
  places: () => get<Place[]>("/places"),
  notifications: () => get<Notifications>("/notifications"),
  markNotificationsRead: () => post<Notifications>("/notifications/read"),

  catalogue: () => get<Catalogue>("/materials"),
  rates: (code: string) => get<Rate[]>(`/materials/${code}/rates`),

  lots: (scope: "mine" | "market", filter: MarketFilter = {}) => {
    const query = new URLSearchParams({ scope });
    if (filter.family) query.set("family", filter.family);
    if (filter.place) query.set("place", filter.place);
    return get<Lot[]>(`/lots?${query}`);
  },
  lot: (id: string) => get<Lot>(`/lots/${id}`),
  createLot: (photo: File) => {
    const form = new FormData();
    form.append("photo", photo);
    return postForm<Lot>("/lots", form);
  },
  confirmLot: (id: string, details: LotDetails) => post<Lot>(`/lots/${id}/confirm`, details),
  listLot: (
    id: string,
    auction_hours: number,
    reserve_rate_paise_per_kg: number | null,
    auction_format: AuctionFormat = "sealed",
  ) => post<Lot>(`/lots/${id}/list`, { auction_hours, reserve_rate_paise_per_kg, auction_format }),
  acceptBid: (id: string, bid_id: number) => post<Lot>(`/lots/${id}/accept`, { bid_id }),
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

  schedulePickup: (id: string, pickupAt: Date, location: { latitude: number; longitude: number } | null) =>
    post<Lot>(`/lots/${id}/pickup`, { pickup_at: pickupAt.toISOString(), ...location }),
  recordDelivery: (id: string, measuredGrams: number, slip: File) => {
    const form = new FormData();
    form.append("measured_weight_grams", String(measuredGrams));
    form.append("slip", slip);
    return postForm<Lot>(`/lots/${id}/delivery`, form);
  },
  assignTransporter: (id: string, transporter_id: number) =>
    post<Lot>(`/lots/${id}/transporter`, { transporter_id }),
  recordPickupWeight: (id: string, weight_grams: number) =>
    post<Lot>(`/lots/${id}/pickup-weight`, { weight_grams }),
  acceptDelivery: (id: string) => post<Lot>(`/lots/${id}/delivery/accept`),
  disputeDelivery: (id: string, reason: string) =>
    post<Lot>(`/lots/${id}/delivery/dispute`, { reason }),
  resolveDispute: (id: string, body: ResolveIn) => post<Lot>(`/lots/${id}/dispute/resolve`, body),
  disputes: () => get<Dispute[]>("/admin/disputes"),

  certificate: (id: string) => get<Certificate>(`/certificates/${id}`),
  verify: (id: string) => get<Verification>(`/certificates/${id}/verify`),
  wallet: () => get<Wallet>("/wallet"),
  invoice: (lotId: string) => get<Invoice>(`/lots/${lotId}/invoice`),
  impact: () => get<Impact>("/impact"),

  rfqs: () => get<Rfq[]>("/rfqs"),
  postRfq: (body: RfqIn) => post<Rfq>("/rfqs", body),
  closeRfq: (id: string) => post<Rfq>(`/rfqs/${id}/close`),

  agreements: () => get<Agreement[]>("/agreements"),
  partners: () => get<Party[]>("/agreements/partners"),
  proposeAgreement: (body: AgreementIn) => post<Agreement>("/agreements", body),
  decideAgreement: (id: string, decision: "accept" | "decline") =>
    post<Agreement>(`/agreements/${id}/${decision}`),

  users: (kycStatus?: string) =>
    get<User[]>(`/admin/users${kycStatus ? `?kyc_status=${kycStatus}` : ""}`),
  decideKyc: (
    userId: string,
    decision: "approve" | "reject",
    note?: string,
    authorisations: Authorisation[] = [],
  ) => post<User>(`/admin/users/${userId}/kyc`, { decision, note: note || null, authorisations }),
  addMaterial: (body: MaterialIn) => post<Material>("/admin/materials", body),
  overview: () => get<Overview>("/admin/overview"),
  setRate: (code: string, rate_paise_per_kg: number) =>
    put<Material>(`/admin/materials/${code}/rate`, { rate_paise_per_kg }),
  transporters: () => get<Transporter[]>("/admin/transporters"),
  addTransporter: (body: TransporterIn) => post<Transporter>("/admin/transporters", body),
  route: (day: string) => get<Route>(`/admin/routes?day=${day}`),
  anchors: () => get<Anchor[]>("/admin/anchors"),
  sealAnchor: () => post<Anchor>("/admin/anchors"),
  checkAnchor: (id: number) => get<{ id: number; holds: boolean }>(`/admin/anchors/${id}/check`),
  jobs: () => get<Job[]>("/admin/jobs"),
  runJob: (name: string) => post<JobRun>(`/admin/jobs/${name}/run`),
};
