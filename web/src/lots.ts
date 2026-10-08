import type { CustodyEvent, Lot, Rate, User } from "./api/client";
import { day, perKg } from "./format";

export type Tone = "quiet" | "live" | "action" | "done" | "held";

const METAL_COLOURS: Record<string, string> = {
  copper: "var(--copper)",
  brass: "var(--brass)",
  aluminium: "var(--aluminium)",
  steel_hms: "var(--steel)",
  cast_iron: "var(--cast-iron)",
  pet_bottles: "var(--plastic)",
  hdpe: "var(--plastic)",
  occ_cardboard: "var(--paper)",
  e_waste_boards: "var(--e-waste)",
  lead_acid_batteries: "var(--battery)",
};

/** Every material keeps its colour from the metal-tag palette; non-metals get one per stream. */
export function metalColour(code: string | null | undefined): string {
  return (code && METAL_COLOURS[code]) || "var(--unknown-metal)";
}

export const FAMILY_NAMES: Record<string, string> = {
  ferrous: "Ferrous metals",
  non_ferrous: "Non-ferrous metals",
  plastic: "Plastics",
  paper: "Paper",
  e_waste: "E-waste",
  battery: "Batteries",
};

/** Regulated materials, named for the authorisation a buyer needs to trade them. */
export const AUTHORISATION_NAMES: Record<string, string> = {
  e_waste: "CPCB e-waste authorisation",
  battery: "CPCB battery waste authorisation",
};

export function isSellerSide(lot: Lot, user: User): boolean {
  return user.role === "admin" || lot.seller.id === user.id;
}

export function isWinner(lot: Lot, user: User): boolean {
  return lot.award?.buyer.id === user.id;
}

/** The winner has paid: from here on the lot belongs to one buyer. */
const SOLD = new Set(["funded", "pickup_scheduled", "delivered", "settled", "disputed", "cancelled"]);

/** What this lot's state means for the person looking at it, in their words. */
export function statusFor(lot: Lot, user: User): { text: string; tone: Tone } {
  const seller = isSellerSide(lot, user);
  const winner = isWinner(lot, user);
  // Their win lapsed (not paid in time, or declined): whatever happens next isn't theirs.
  if (lot.my_bid_lapsed && !winner) return { text: "You didn't buy this lot", tone: "quiet" };
  // A bidder who lost: once the winner has paid, the rest of the trade isn't theirs either.
  if (user.role === "buyer" && !winner && SOLD.has(lot.status)) return { text: "Sold to another buyer", tone: "quiet" };
  switch (lot.status) {
    case "draft":
      return { text: "Not listed yet", tone: "action" };
    case "listed":
      return { text: "Taking bids", tone: "live" };
    case "awarded":
      if (winner) return { text: "You won. Pay to confirm", tone: "action" };
      if (seller) return { text: "Sold. Waiting for payment", tone: "live" };
      return { text: "Bidding closed", tone: "quiet" };
    case "unsold":
      return { text: "No winning bid", tone: "quiet" };
    case "funded":
      return { text: "Paid into escrow. Book pickup", tone: "action" };
    case "pickup_scheduled":
      return winner
        ? { text: "Pickup booked. Weigh on arrival", tone: "action" }
        : { text: "Pickup booked", tone: "live" };
    case "delivered":
      return seller
        ? { text: "Weighed. Check the reading", tone: "action" }
        : { text: "Weighed. Waiting for seller", tone: "live" };
    case "settled":
      return { text: "Paid out", tone: "done" };
    case "disputed":
      return { text: "On hold", tone: "held" };
    case "cancelled":
      return { text: "Cancelled. Buyer refunded", tone: "quiet" };
    default:
      return { text: lot.status, tone: "quiet" };
  }
}

/** The custody record's event names, as people would say them. */
export const EVENT_TEXT: Record<string, string> = {
  "lot.created": "Photographed",
  "lot.confirmed": "Metal, grade and weight confirmed",
  "lot.listed": "Listed for bids",
  "auction.closed": "Bidding closed",
  "escrow.funded": "Buyer paid into escrow",
  "pickup.scheduled": "Pickup booked",
  "delivery.recorded": "Weighed at the weighbridge",
  "delivery.accepted": "Seller accepted the weight",
  "delivery.disputed": "Seller reported a problem",
  "settlement.blocked": "Payment held: weight above what was paid in",
  "settlement.completed": "Paid out",
  "payment.returned": "Late payment returned to the buyer's wallet",
};

/** One line for a custody event; a few depend on what the event recorded, not just its type. */
export function eventText(event: CustodyEvent): string {
  if (event.event_type === "dispute.resolved") {
    return event.payload.outcome === "cancelled"
      ? "Dispute resolved: trade cancelled, buyer refunded"
      : "Dispute resolved: settled at the agreed weight";
  }
  if (event.event_type === "award.lapsed") {
    const who =
      event.payload.reason === "declined" ? "Winning buyer declined" : "Winning buyer didn't pay in time";
    return event.payload.result === "awarded" ? `${who}. Passed to the next bidder` : `${who}. Not sold`;
  }
  return EVENT_TEXT[event.event_type] ?? event.event_type;
}

function change(to: number, from: number): string {
  const tenths = Math.round((Math.abs(to - from) * 1000) / from);
  return `${to >= from ? "up" : "down"} ${tenths / 10}% from ${perKg(from)}`;
}

/** Why a reference price is what it is, in a sentence the seller can check. */
export function rateReason(rate: Rate): string {
  const from = rate.previous_rate_paise_per_kg;
  const on = day(rate.effective_from);
  if (rate.source === "seed") {
    return "ScrapLink's starting price. It follows the market once enough paid trades come in.";
  }
  if (rate.source === "admin" || from === null) {
    return `Set by ScrapLink on ${on}${from ? `, ${change(rate.rate_paise_per_kg, from)}` : ""}.`;
  }
  const reason =
    `Moved ${change(rate.rate_paise_per_kg, from)} on ${on}, after ${rate.trade_count} paid trades ` +
    `in the past ${rate.window_days} days. Their middle price was ${perKg(rate.market_median_paise_per_kg!)} ` +
    "for grade A.";
  if (!rate.capped) return reason;
  const way = rate.market_median_paise_per_kg! > rate.rate_paise_per_kg ? "rise" : "fall";
  return `${reason} Prices move a limited amount at a time, so it may ${way} further.`;
}

/** The same, in a few words, for a list of past prices. */
export function rateSource(rate: Rate): string {
  if (rate.source === "seed") return "Starting price";
  if (rate.source === "admin") return "Set by an admin";
  return `${rate.trade_count} paid trades${rate.capped ? ", move limited" : ""}`;
}
