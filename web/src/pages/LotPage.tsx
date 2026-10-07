import { useEffect, useState, type CSSProperties, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError, api, fetchBlob, type Escrow, type Lot, type User } from "../api/client";
import { useUser } from "../auth";
import { AuthedImage, ErrorNote, Field, Loading, useAction, useLoad } from "../components";
import { amountFor, kg, parseKg, parseRupees, perKg, rupees, timeLeft, when } from "../format";
import { AUTHORISATION_NAMES, eventText, isSellerSide, isWinner, metalColour, statusFor } from "../lots";

const WAITING_ON_SOMEONE = new Set(["listed", "awarded", "funded", "pickup_scheduled", "delivered"]);

export function LotPage() {
  const { id = "" } = useParams();
  const user = useUser();
  const lot = useLoad(() => api.lot(id), [id]);
  const { reload } = lot;
  const status = lot.data?.status;

  // The other party acts on their own phone; keep this view current without a manual refresh.
  useEffect(() => {
    if (!status || !WAITING_ON_SOMEONE.has(status)) return;
    const timer = window.setInterval(() => void reload(), 15000);
    return () => window.clearInterval(timer);
  }, [status, reload]);

  if (lot.error) return <ErrorNote message={lot.error} />;
  if (!lot.data) return <Loading />;
  const l = lot.data;
  const update = (next: Lot) => lot.setData(next);
  const party = isSellerSide(l, user) || isWinner(l, user);
  const state = statusFor(l, user);

  return (
    <article className="lot" style={{ "--metal": metalColour(l.material_code) } as CSSProperties}>
      <AuthedImage path={l.photo_url} alt={`Photo of ${l.material_name ?? "the lot"}`} className="photo-hero" />
      <header className="lot-head">
        <h1>{l.material_name ?? "Material not chosen yet"}</h1>
        <p className={`status status-${state.tone}`}>{state.text}</p>
        <dl className="facts">
          {l.grade && <Fact label="Condition" value={`Grade ${l.grade}`} />}
          {l.declared_weight_grams != null && <Fact label="Seller's weight" value={kg(l.declared_weight_grams)} />}
          {l.measured_weight_grams != null && <Fact label="Weighbridge" value={kg(l.measured_weight_grams)} />}
          {l.estimate && (
            <Fact label="Fair price" value={`${rupees(l.estimate.low_paise)} – ${rupees(l.estimate.high_paise)}`} />
          )}
          {l.award && <Fact label="Winning bid" value={perKg(l.award.rate_paise_per_kg)} />}
          {l.settled_amount_paise != null && <Fact label="Paid to seller" value={rupees(l.settled_amount_paise)} />}
          {!isSellerSide(l, user) && <Fact label="Seller" value={l.seller.business_name ?? l.seller.name} />}
          {l.material_authorisation && (
            <Fact label="Buyers" value={`${AUTHORISATION_NAMES[l.material_authorisation]} holders only`} />
          )}
        </dl>
      </header>

      <NextStep lot={l} user={user} onChange={update} />

      {party && <ClosedBids lot={l} user={user} />}
      {party && <Record lotId={l.id} version={l.status} />}
    </article>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="fact">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

/** The one thing this person can do now, or what they are waiting for. */
function NextStep({ lot, user, onChange }: { lot: Lot; user: User; onChange: (lot: Lot) => void }) {
  const seller = isSellerSide(lot, user);
  const winner = isWinner(lot, user);
  // A bidder who isn't the buyer: they can still see the lot, but none of its next steps are theirs.
  const otherBidder = !seller && !winner;
  if (otherBidder && lot.my_bid_lapsed) return <LapsedNote />;

  switch (lot.status) {
    case "draft":
      return seller ? (
        <section className="panel">
          <h2>Finish listing</h2>
          <Link className="btn-primary" to={`/lots/${lot.id}/${lot.estimate ? "sell" : "details"}`}>
            Continue
          </Link>
        </section>
      ) : null;
    case "listed":
      if (user.role === "buyer" && lot.material_authorisation && !user.authorisations.includes(lot.material_authorisation))
        return <NeedsAuthorisation authorisation={lot.material_authorisation} />;
      return user.role === "buyer" ? (
        <BidForm lot={lot} onChange={onChange} />
      ) : (
        <section className="panel">
          <h2>Taking bids</h2>
          <p>
            {lot.bid_count === 0 ? "No bids yet." : `${lot.bid_count} ${lot.bid_count === 1 ? "bid" : "bids"} so far.`}{" "}
            Bidding closes {when(lot.auction_closes_at!)} ({timeLeft(lot.auction_closes_at!)}).
          </p>
          {lot.reserve_rate_paise_per_kg && (
            <p className="note">Your lowest price is {perKg(lot.reserve_rate_paise_per_kg)}. Buyers can't see it.</p>
          )}
          <p className="note">Bids are sealed until bidding closes, so you'll see them all at once.</p>
        </section>
      );
    case "awarded":
      if (winner) return <PayPanel lot={lot} user={user} onChange={onChange} />;
      if (seller && lot.award)
        return (
          <section className="panel">
            <h2>Sold to {lot.award.buyer.business_name ?? lot.award.buyer.name}</h2>
            <p>
              They bid {perKg(lot.award.rate_paise_per_kg)} and now pay {rupees(lot.award.escrow_required_paise)} into
              escrow. Once it's paid you can book the pickup.
            </p>
            {lot.award.escrow_due_at && (
              <p className="note">
                They have until {when(lot.award.escrow_due_at)} to pay. If they don't, the lot goes to the next highest
                bidder.
              </p>
            )}
          </section>
        );
      return (
        <section className="panel">
          <p>
            Bidding has closed and another buyer won this lot. If they don't pay in time, it passes to the next highest
            bidder.
          </p>
        </section>
      );
    case "unsold":
      return (
        <section className="panel">
          <p>
            {lot.bid_count === 0
              ? "Nobody bid on this lot."
              : "Not sold. Either no bid reached the lowest price, or the winning buyers didn't go ahead."}
          </p>
        </section>
      );
    case "funded":
    case "pickup_scheduled":
      if (otherBidder) return <SoldElsewhere />;
      return (
        <>
          <PickupPanel lot={lot} onChange={onChange} />
          {winner && lot.status === "pickup_scheduled" && <DeliveryForm lot={lot} onChange={onChange} />}
        </>
      );
    case "delivered":
      if (seller) return <ReviewWeight lot={lot} onChange={onChange} />;
      if (otherBidder) return <SoldElsewhere />;
      return (
        <section className="panel">
          <h2>Waiting for the seller</h2>
          <p>The seller is checking your weighbridge reading. Payment is released once they accept it.</p>
        </section>
      );
    case "settled":
      if (otherBidder) return <SoldElsewhere />;
      return lot.certificate_id ? <CertificatePanel lotId={lot.id} certificateId={lot.certificate_id} /> : null;
    case "disputed":
      if (otherBidder) return <SoldElsewhere />;
      return (
        <section className="panel panel-held">
          <h2>On hold</h2>
          <p>
            The money stays in escrow while ScrapLink checks what happened. Support will contact both of you.
          </p>
        </section>
      );
    default:
      return null;
  }
}

function BidForm({ lot, onChange }: { lot: Lot; onChange: (lot: Lot) => void }) {
  const mine = lot.my_bid_rate_paise_per_kg;
  const [rate, setRate] = useState(mine ? String(mine / 100) : "");
  const action = useAction();
  const paise = parseRupees(rate);
  const grams = lot.declared_weight_grams!;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!paise) return;
    void action.run(async () => onChange(await api.bid(lot.id, paise)));
  };

  return (
    <section className="panel">
      <h2>{mine ? "Your bid" : "Place a bid"}</h2>
      <p>
        Bidding closes {when(lot.auction_closes_at!)} ({timeLeft(lot.auction_closes_at!)}). Other buyers can't see your
        bid.
      </p>
      {mine && <p className="confirmed">You bid {perKg(mine)}. You can change it until bidding closes.</p>}
      <form onSubmit={submit} className="stack">
        <Field
          label="Your price per kg (₹)"
          inputMode="decimal"
          required
          value={rate}
          onChange={(e) => setRate(e.target.value)}
          hint={
            paise
              ? `About ${rupees(amountFor(paise, grams))} for the seller's ${kg(grams)}. You pay for the weighbridge weight.`
              : `Reference price: ${perKg(lot.estimate!.rate_paise_per_kg)}`
          }
        />
        <ErrorNote message={action.error} />
        <button className="btn-primary" disabled={!paise || action.busy}>
          {mine ? "Change bid" : "Place bid"}
        </button>
      </form>
    </section>
  );
}

declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => { open: () => void };
  }
}

function loadCheckout(): Promise<void> {
  if (window.Razorpay) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve();
    script.onerror = () => reject(new ApiError(0, "Couldn't open the payment page. Check your connection."));
    document.head.append(script);
  });
}

async function payWithRazorpay(escrow: Escrow): Promise<void> {
  await loadCheckout();
  return new Promise((resolve, reject) => {
    new window.Razorpay!({
      key: escrow.razorpay_key_id,
      order_id: escrow.gateway_order_id,
      amount: escrow.amount_paise,
      currency: "INR",
      name: "ScrapLink",
      description: "Escrow for a scrap lot",
      handler: (result: { razorpay_order_id: string; razorpay_payment_id: string; razorpay_signature: string }) =>
        api.razorpayVerify(result).then(() => resolve(), reject),
      modal: { ondismiss: () => reject(new ApiError(0, "Payment cancelled. You can try again.")) },
    }).open();
  });
}

function PayPanel({ lot, user, onChange }: { lot: Lot; user: User; onChange: (lot: Lot) => void }) {
  const action = useAction();
  const decline = useAction();
  const [confirmingDecline, setConfirmingDecline] = useState(false);
  const amount = lot.award!.escrow_required_paise;
  const due = lot.award!.escrow_due_at;

  // This page may have been open since before the deadline. If an action is refused because the
  // lot has moved on, show where it stands now rather than an error under a stale "You won".
  const unlessMovedOn = (run: () => Promise<void>) => async () => {
    try {
      await run();
    } catch (err) {
      const now = await api.lot(lot.id).catch(() => null);
      if (now && (now.status !== "awarded" || !isWinner(now, user))) return onChange(now);
      throw err;
    }
  };

  const pay = () =>
    action.run(
      unlessMovedOn(async () => {
        const escrow = await api.startEscrow(lot.id);
        if (escrow.gateway === "simulated") await api.simulateCapture(escrow.intent_id);
        else await payWithRazorpay(escrow);
        onChange(await api.lot(lot.id));
      }),
    );

  return (
    <section className="panel">
      <h2>You won at {perKg(lot.award!.rate_paise_per_kg)}</h2>
      <p>
        Pay {rupees(amount)} into escrow. ScrapLink holds it until the lot is weighed: you pay only for the weight that
        arrives, and anything left over comes back to your wallet.
      </p>
      {due && (
        <p className="deadline">
          Pay by {when(due)} ({timeLeft(due)}). After that the lot goes to the next highest bidder.
        </p>
      )}
      <ErrorNote message={action.error} />
      <button type="button" className="btn-primary" disabled={action.busy} onClick={() => void pay()}>
        Pay {rupees(amount)}
      </button>

      <div className="decline">
        {confirmingDecline ? (
          <>
            <p>
              The lot goes to the next highest bidder straight away, and you can't undo this.
            </p>
            <ErrorNote message={decline.error} />
            <div className="row">
              <button
                type="button"
                className="btn-danger"
                disabled={decline.busy}
                onClick={() =>
                  void decline.run(unlessMovedOn(async () => onChange(await api.declineAward(lot.id))))
                }
              >
                Yes, I can't buy it
              </button>
              <button type="button" className="btn" onClick={() => setConfirmingDecline(false)}>
                Keep it
              </button>
            </div>
          </>
        ) : (
          <button type="button" className="btn-quiet" onClick={() => setConfirmingDecline(true)}>
            I can't buy this lot
          </button>
        )}
      </div>
    </section>
  );
}

function NeedsAuthorisation({ authorisation }: { authorisation: string }) {
  return (
    <section className="panel panel-held">
      <h2>Authorised recyclers only</h2>
      <p>
        This lot can be sold only to buyers holding a {AUTHORISATION_NAMES[authorisation] ?? authorisation}. Your account
        doesn't have one recorded, so you can't bid. Contact ScrapLink support to add it.
      </p>
    </section>
  );
}

function SoldElsewhere() {
  return (
    <section className="panel">
      <h2>Sold to another buyer</h2>
      <p>Another buyer won this lot and paid for it, so there's nothing more for you to do here.</p>
    </section>
  );
}

function LapsedNote() {
  return (
    <section className="panel">
      <h2>You didn't buy this lot</h2>
      <p>
        Your win lapsed because it wasn't paid for in time, or you declined it. If a payment went through after the
        deadline, the money is in your <Link to="/wallet">wallet</Link>.
      </p>
    </section>
  );
}

function tomorrowAtTen(): string {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  d.setHours(10, 0, 0, 0);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T10:00`;
}

/** "9.9312, 76.2673" to a point; null for empty or unreadable text. */
function parseLocation(text: string): { latitude: number; longitude: number } | null {
  const match = /^\s*(-?\d{1,2}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)\s*$/.exec(text);
  if (!match) return null;
  const [latitude, longitude] = [Number(match[1]), Number(match[2])];
  return Math.abs(latitude) <= 90 && Math.abs(longitude) <= 180 ? { latitude, longitude } : null;
}

function PickupPanel({ lot, onChange }: { lot: Lot; onChange: (lot: Lot) => void }) {
  const [at, setAt] = useState(tomorrowAtTen);
  const [where, setWhere] = useState(
    lot.pickup_location ? `${lot.pickup_location.latitude}, ${lot.pickup_location.longitude}` : "",
  );
  const [editing, setEditing] = useState(lot.status === "funded");
  const action = useAction();
  const location = parseLocation(where);

  const useMyLocation = () => {
    if (!navigator.geolocation) return action.setError("This phone can't share its location. Type it instead.");
    navigator.geolocation.getCurrentPosition(
      (position) =>
        setWhere(`${position.coords.latitude.toFixed(5)}, ${position.coords.longitude.toFixed(5)}`),
      () => action.setError("Couldn't get your location. Type it instead, or leave it empty."),
    );
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    void action.run(async () => {
      onChange(await api.schedulePickup(lot.id, new Date(at), location));
      setEditing(false);
    });
  };

  return (
    <section className="panel">
      <h2>Pickup</h2>
      {lot.pickup_at && !editing ? (
        <p>
          Booked for {when(lot.pickup_at)}.{" "}
          <button type="button" className="btn-quiet" onClick={() => setEditing(true)}>
            Change time
          </button>
        </p>
      ) : (
        <form onSubmit={submit} className="stack">
          <p>The buyer's money is in escrow. Agree a time with each other and book it here.</p>
          <Field label="Pickup time" type="datetime-local" required value={at} onChange={(e) => setAt(e.target.value)} />
          <Field
            label="Pickup location (optional)"
            inputMode="decimal"
            placeholder="9.9312, 76.2673"
            value={where}
            onChange={(e) => setWhere(e.target.value)}
            hint={
              <>
                Latitude, longitude. Helps plan the truck's route.{" "}
                <button type="button" className="btn-quiet" onClick={useMyLocation}>
                  Use my location
                </button>
              </>
            }
          />
          {where && !location && <p className="error-note">Enter it as two numbers, like 9.9312, 76.2673</p>}
          <ErrorNote message={action.error} />
          <button className="btn-primary" disabled={action.busy || (where !== "" && !location)}>
            Book pickup
          </button>
        </form>
      )}
    </section>
  );
}

function DeliveryForm({ lot, onChange }: { lot: Lot; onChange: (lot: Lot) => void }) {
  const [weight, setWeight] = useState("");
  const [slip, setSlip] = useState<File | null>(null);
  const action = useAction();
  const grams = parseKg(weight);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!grams || !slip) return;
    void action.run(async () => onChange(await api.recordDelivery(lot.id, grams, slip)));
  };

  return (
    <section className="panel">
      <h2>Weighbridge reading</h2>
      <p>After weighing, enter the net weight and photograph the slip. The seller checks it before payment.</p>
      <form onSubmit={submit} className="stack">
        <Field
          label="Net weight in kg"
          inputMode="decimal"
          required
          value={weight}
          onChange={(e) => setWeight(e.target.value)}
          hint={`The seller said ${kg(lot.declared_weight_grams!)}.`}
        />
        <label className="field">
          <span className="field-label">Photo of the weighbridge slip</span>
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            capture="environment"
            required
            onChange={(e) => setSlip(e.target.files?.[0] ?? null)}
          />
        </label>
        <ErrorNote message={action.error} />
        <button className="btn-primary" disabled={!grams || !slip || action.busy}>
          Send reading
        </button>
      </form>
    </section>
  );
}

function ReviewWeight({ lot, onChange }: { lot: Lot; onChange: (lot: Lot) => void }) {
  const [reporting, setReporting] = useState(false);
  const [reason, setReason] = useState("");
  const action = useAction();
  const measured = lot.measured_weight_grams!;
  const declared = lot.declared_weight_grams!;
  const payable = amountFor(lot.award!.rate_paise_per_kg, measured);
  const difference = measured - declared;

  return (
    <section className="panel">
      <h2>Check the weighbridge reading</h2>
      <AuthedImage path={`/lots/${lot.id}/weighbridge-slip`} alt="Weighbridge slip" className="photo-slip" />
      <dl className="facts">
        <Fact label="You said" value={kg(declared)} />
        <Fact label="Weighbridge" value={kg(measured)} />
        <Fact label="Difference" value={`${difference >= 0 ? "+" : "−"}${kg(Math.abs(difference))}`} />
        <Fact label="You'll be paid" value={rupees(payable)} />
      </dl>
      {payable > lot.award!.escrow_required_paise && (
        <p className="error-note">
          This is more than the buyer paid into escrow. If you accept, the trade goes on hold until ScrapLink sorts out
          the difference.
        </p>
      )}
      <ErrorNote message={action.error} />
      {reporting ? (
        <form
          className="stack"
          onSubmit={(e) => {
            e.preventDefault();
            void action.run(async () => onChange(await api.disputeDelivery(lot.id, reason)));
          }}
        >
          <label className="field">
            <span className="field-label">What's wrong?</span>
            <textarea required minLength={3} value={reason} onChange={(e) => setReason(e.target.value)} />
          </label>
          <div className="row">
            <button className="btn-danger" disabled={action.busy}>
              Report problem
            </button>
            <button type="button" className="btn" onClick={() => setReporting(false)}>
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <div className="row">
          <button
            type="button"
            className="btn-primary"
            disabled={action.busy}
            onClick={() => void action.run(async () => onChange(await api.acceptDelivery(lot.id)))}
          >
            Accept and get paid
          </button>
          <button type="button" className="btn" onClick={() => setReporting(true)}>
            Report a problem
          </button>
        </div>
      )}
    </section>
  );
}

function CertificatePanel({ lotId, certificateId }: { lotId: string; certificateId: string }) {
  const certificate = useLoad(() => api.certificate(certificateId), [certificateId]);
  const action = useAction();

  const download = () =>
    action.run(async () => {
      const blob = await fetchBlob(certificate.data!.pdf_url);
      const url = URL.createObjectURL(blob);
      const link = Object.assign(document.createElement("a"), {
        href: url,
        download: `scraplink-certificate-${certificateId}.pdf`,
      });
      link.click();
      URL.revokeObjectURL(url);
    });

  return (
    <section className="panel panel-done">
      <h2>Trade complete</h2>
      <p>
        The certificate records every step of this trade. Each step is sealed to the one before, so any later change
        shows up when the certificate is checked.
      </p>
      <ErrorNote message={certificate.error ?? action.error} />
      <div className="row">
        <button type="button" className="btn-primary" disabled={!certificate.data || action.busy} onClick={() => void download()}>
          Download certificate
        </button>
        <Link className="btn" to={`/certificates/${certificateId}/verify`}>
          Check certificate
        </Link>
        <Link className="btn" to={`/lots/${lotId}/invoice`}>
          View invoice
        </Link>
      </div>
    </section>
  );
}

function ClosedBids({ lot, user }: { lot: Lot; user: User }) {
  const visible = lot.status !== "listed" && lot.status !== "draft" && isSellerSide(lot, user);
  const bids = useLoad(() => (visible ? api.bids(lot.id) : Promise.resolve([])), [lot.id, visible]);
  if (!visible || !bids.data?.length) return null;
  return (
    <section className="panel">
      <h2>Bids</h2>
      <ol className="bids">
        {bids.data.map((b, i) => (
          <li
            key={i}
            className={b.lapsed ? "bid-lapsed" : b.buyer.id === lot.award?.buyer.id ? "bid-buyer" : undefined}
          >
            <span>
              {b.buyer.business_name ?? b.buyer.name}
              {b.lapsed && <span className="bid-note">Won, but didn't buy</span>}
              {!b.lapsed && b.buyer.id === lot.award?.buyer.id && <span className="bid-note">Buyer</span>}
            </span>
            <span>{perKg(b.rate_paise_per_kg)}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}

function Record({ lotId, version }: { lotId: string; version: string }) {
  const events = useLoad(() => api.custody(lotId), [lotId, version]);
  if (!events.data?.length) return null;
  return (
    <section className="record">
      <h2>Record</h2>
      <ol className="timeline">
        {events.data.map((e) => (
          <li key={e.seq}>
            <span className="timeline-what">{eventText(e)}</span>
            <span className="timeline-when">{when(e.recorded_at)}</span>
            <code className="timeline-seal" title={e.hash}>
              {e.hash.slice(0, 12)}
            </code>
          </li>
        ))}
      </ol>
    </section>
  );
}
