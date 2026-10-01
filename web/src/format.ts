// Money arrives as integer paise and weight as integer grams. Parsing typed input goes through
// string arithmetic, never floats, so "176.4" kg is exactly 176400 g.

const wholeRupees = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});
const exactRupees = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 2,
});
const kilos = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 3 });

export function rupees(paise: number): string {
  return paise % 100 === 0 ? wholeRupees.format(paise / 100) : exactRupees.format(paise / 100);
}

export function perKg(paise: number): string {
  return `${rupees(paise)}/kg`;
}

export function kg(grams: number): string {
  return `${kilos.format(grams / 1000)} kg`;
}

function parseScaled(text: string, decimals: number): number | null {
  const clean = text.trim().replace(/,/g, "");
  const match = new RegExp(`^(\\d+)(?:\\.(\\d{1,${decimals}}))?$`).exec(clean);
  if (!match) return null;
  const whole = Number(match[1]);
  const fraction = Number((match[2] ?? "").padEnd(decimals, "0"));
  const value = whole * 10 ** decimals + fraction;
  return Number.isSafeInteger(value) && value > 0 ? value : null;
}

export const parseKg = (text: string) => parseScaled(text, 3);
export const parseRupees = (text: string) => parseScaled(text, 2);

/** paise x grams / 1000, rounded half up — the backend's `amount_for`. */
export function amountFor(ratePaisePerKg: number, grams: number): number {
  return Math.floor((ratePaisePerKg * grams + 500) / 1000);
}

const dateTime = new Intl.DateTimeFormat("en-IN", {
  day: "numeric",
  month: "short",
  hour: "numeric",
  minute: "2-digit",
});

export function when(iso: string): string {
  return dateTime.format(new Date(iso));
}

export function timeLeft(iso: string, now = Date.now()): string {
  const minutes = Math.round((new Date(iso).getTime() - now) / 60000);
  if (minutes <= 0) return "closing now";
  if (minutes < 60) return `${minutes} min left`;
  const hours = Math.floor(minutes / 60);
  if (hours < 48) return `${hours} h ${minutes % 60} min left`;
  return `${Math.floor(hours / 24)} days left`;
}
