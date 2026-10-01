import { useEffect, useState, type CSSProperties, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError, api, fetchBlob, type Escrow, type Lot, type User } from "../api/client";
import { useUser } from "../auth";
import { AuthedImage, ErrorNote, Field, Loading, useAction, useLoad } from "../components";
import { amountFor, kg, parseKg, parseRupees, perKg, rupees, timeLeft, when } from "../format";
import { eventText, isSellerSide, isWinner, metalColour, statusFor } from "../lots";

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
        <h1>{l.material_name ?? "Metal not chosen yet"}</h1>
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
      if (winner) return <PayPanel lot={lot} onChange={onChange} />;
      if (lot.my_bid_lapsed) return <LapsedNote />;
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
          <p>Bidding has closed and another buyer won this lot.</p>
        </section>
      );
    case "unsold":
      if (lot.my_bid_lapsed) return <LapsedNote />;
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
      if (!seller && !winner) return null;
      return (
        <>
          <PickupPanel lot={lot} onChange={onChange} />
          {winner && lot.status === "pickup_scheduled" && <DeliveryForm lot={lot} onChange={onChange} />}
        </>
      );
    case "delivered":
      if (seller) return <ReviewWeight lot={lot} onChange={onChange} />;
      return (
        <section className="panel">
          <h2>Waiting for the seller</h2>
          <p>The seller is checking your weighbridge reading. Payment is released once they accept it.</p>
        </section>
      );
    case "settled":
      return lot.certificate_id ? <CertificatePanel certificateId={lot.certificate_id} /> : null;
    case "disputed":
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

function PayPanel({ lot, onChange }: { lot: Lot; onChange: (lot: Lot) => void }) {
  const action = useAction();
  const decline = useAction();
  const [confirmingDecline, setConfirmingDecline] = useState(false);
  const amount = lot.award!.escrow_required_paise;
  const due = lot.award!.escrow_due_at;

  const pay = () =>
    action.run(async () => {
      const escrow = await api.startEscrow(lot.id);
      if (escrow.gateway === "simulated") await api.simulateCapture(escrow.intent_id);
      else await payWithRazorpay(escrow);
      onChange(await api.lot(lot.id));
    });

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
                onClick={() => void decline.run(async () => onChange(await api.declineAward(lot.id)))}
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

function PickupPanel({ lot, onChange }: { lot: Lot; onChange: (lot: Lot) => void }) {
  const [at, setAt] = useState(tomorrowAtTen);
  const [editing, setEditing] = useState(lot.status === "funded");
  const action = useAction();

  const submit = (event: FormEvent) => {
    event.preventDefault();
    void action.run(async () => {
      onChange(await api.schedulePickup(lot.id, new Date(at)));
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
          <ErrorNote message={action.error} />
          <button className="btn-primary" disabled={action.busy}>
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

function CertificatePanel({ certificateId }: { certificateId: string }) {
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
          <li key={i}>
            <span>{b.buyer.business_name ?? b.buyer.name}</span>
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
