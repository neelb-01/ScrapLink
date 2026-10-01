import type { CustodyEvent, Lot, User } from "./api/client";

export type Tone = "quiet" | "live" | "action" | "done" | "held";

const METAL_COLOURS: Record<string, string> = {
  copper: "var(--copper)",
  brass: "var(--brass)",
  aluminium: "var(--aluminium)",
  steel_hms: "var(--steel)",
  cast_iron: "var(--cast-iron)",
};

export function metalColour(code: string | null | undefined): string {
  return (code && METAL_COLOURS[code]) || "var(--unknown-metal)";
}

export function isSellerSide(lot: Lot, user: User): boolean {
  return user.role === "admin" || lot.seller.id === user.id;
}

export function isWinner(lot: Lot, user: User): boolean {
  return lot.award?.buyer.id === user.id;
}

/** What this lot's state means for the person looking at it, in their words. */
export function statusFor(lot: Lot, user: User): { text: string; tone: Tone } {
  const seller = isSellerSide(lot, user);
  const winner = isWinner(lot, user);
  // Their win lapsed (not paid in time, or declined): whatever happens next isn't theirs.
  if (lot.my_bid_lapsed && !winner) return { text: "You didn't buy this lot", tone: "quiet" };
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
  if (event.event_type === "award.lapsed") {
    const who =
      event.payload.reason === "declined" ? "Winning buyer declined" : "Winning buyer didn't pay in time";
    return event.payload.result === "awarded" ? `${who}. Passed to the next bidder` : `${who}. Not sold`;
  }
  return EVENT_TEXT[event.event_type] ?? event.event_type;
}
