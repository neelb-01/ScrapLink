import { useState, type CSSProperties, type FormEvent } from "react";
import { api, type Agreement, type User } from "../api/client";
import { useUser } from "../auth";
import { ErrorNote, Field, Loading, useAction, useLoad } from "../components";
import { amountFor, day, kg, parseKg, parseRupees, perKg, rupees } from "../format";
import { metalColour } from "../lots";
import { MaterialSelect } from "./Requests";

// Supply agreements, first slice: a buyer offers a fixed monthly quantity at a fixed rate to a
// seller they've bought from, and the seller accepts or declines. Monthly call-offs come next.

const STATUS_TEXT: Record<string, string> = {
  proposed: "Waiting for the seller",
  active: "Active",
  declined: "Declined",
};

export function Agreements() {
  const user = useUser();
  const agreements = useLoad(() => api.agreements(), []);
  return (
    <>
      <h1>Supply agreements</h1>
      <p className="lede">
        A regular monthly quantity at a price agreed in advance, so neither side has to auction every load.
      </p>
      {user.role === "buyer" && <OfferForm user={user} onOffered={() => void agreements.reload()} />}
      <ErrorNote message={agreements.error} />
      {!agreements.data && !agreements.error && <Loading />}
      {agreements.data?.length === 0 && (
        <p className="empty">
          {user.role === "seller"
            ? "No buyer has offered you an agreement yet. They can once they've bought a lot from you."
            : "No agreements yet."}
        </p>
      )}
      <ul className="queue">
        {agreements.data?.map((a) => (
          <AgreementCard key={a.id} agreement={a} user={user} onChange={() => void agreements.reload()} />
        ))}
      </ul>
    </>
  );
}

function AgreementCard({ agreement: a, user, onChange }: { agreement: Agreement; user: User; onChange: () => void }) {
  const action = useAction();
  const other = user.id === a.seller.id ? a.buyer : a.seller;
  const decide = (decision: "accept" | "decline") =>
    action.run(async () => {
      await api.decideAgreement(a.id, decision);
      onChange();
    });

  return (
    <li className="panel card" style={{ "--metal": metalColour(a.material_code) } as CSSProperties}>
      <h2>
        {kg(a.monthly_quantity_grams)} of {a.material_name} a month
      </h2>
      <p className={`status status-${a.status === "active" ? "done" : a.status === "proposed" ? "live" : "quiet"}`}>
        {user.id === a.seller.id && a.status === "proposed" ? "Offered to you" : STATUS_TEXT[a.status] ?? a.status}
      </p>
      <dl className="facts">
        <div className="fact">
          <dt>{user.role === "admin" ? "Buyer and seller" : user.id === a.seller.id ? "Buyer" : "Seller"}</dt>
          <dd>
            {user.role === "admin"
              ? `${a.buyer.business_name ?? a.buyer.name}, ${a.seller.business_name ?? a.seller.name}`
              : other.business_name ?? other.name}
          </dd>
        </div>
        <div className="fact">
          <dt>Price</dt>
          <dd>{perKg(a.rate_paise_per_kg)}</dd>
        </div>
        <div className="fact">
          <dt>Each month</dt>
          <dd>{rupees(amountFor(a.rate_paise_per_kg, a.monthly_quantity_grams))}</dd>
        </div>
        <div className="fact">
          <dt>Runs</dt>
          <dd>
            {a.months} months from {day(a.starts_on)}
          </dd>
        </div>
      </dl>
      <ErrorNote message={action.error} />
      {user.id === a.seller.id && a.status === "proposed" && (
        <div className="row">
          <button type="button" className="btn-primary" disabled={action.busy} onClick={() => void decide("accept")}>
            Accept
          </button>
          <button type="button" className="btn" disabled={action.busy} onClick={() => void decide("decline")}>
            Decline
          </button>
        </div>
      )}
    </li>
  );
}

function firstOfNextMonth(): string {
  const d = new Date();
  const next = new Date(d.getFullYear(), d.getMonth() + 1, 1);
  return `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, "0")}-01`;
}

function OfferForm({ user, onOffered }: { user: User; onOffered: () => void }) {
  const data = useLoad(() => Promise.all([api.partners(), api.catalogue()]), []);
  const [seller, setSeller] = useState("");
  const [material, setMaterial] = useState("");
  const [quantity, setQuantity] = useState("");
  const [rate, setRate] = useState("");
  const [startsOn, setStartsOn] = useState(firstOfNextMonth);
  const [months, setMonths] = useState(6);
  const action = useAction();
  const grams = parseKg(quantity);
  const paise = parseRupees(rate);

  if (data.error) return <ErrorNote message={data.error} />;
  if (!data.data) return <Loading />;
  const [partners, catalogue] = data.data;
  if (partners.length === 0)
    return (
      <p className="empty">
        Once you've bought a lot from a seller, you can offer them a supply agreement here.
      </p>
    );

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!seller || !material || !grams || !paise) return;
    void action.run(async () => {
      await api.proposeAgreement({
        seller_id: seller,
        material_code: material,
        monthly_quantity_grams: grams,
        rate_paise_per_kg: paise,
        starts_on: startsOn,
        months,
      });
      setQuantity("");
      setRate("");
      onOffered();
    });
  };

  return (
    <section className="panel">
      <h2>Offer an agreement</h2>
      <form className="stack" onSubmit={submit}>
        <label className="field">
          <span className="field-label">Seller</span>
          <select required value={seller} onChange={(e) => setSeller(e.target.value)}>
            <option value="" disabled>
              Choose a seller you've bought from
            </option>
            {partners.map((p) => (
              <option key={p.id} value={p.id}>
                {p.business_name ?? p.name}
              </option>
            ))}
          </select>
        </label>
        <MaterialSelect materials={catalogue.materials} value={material} onChange={setMaterial} user={user} />
        <Field label="Kg each month" inputMode="decimal" required value={quantity} onChange={(e) => setQuantity(e.target.value)} />
        <Field
          label="Price per kg (₹)"
          inputMode="decimal"
          required
          value={rate}
          onChange={(e) => setRate(e.target.value)}
          hint={grams && paise ? `About ${rupees(amountFor(paise, grams))} a month.` : undefined}
        />
        <Field label="Starts on" type="date" required value={startsOn} onChange={(e) => setStartsOn(e.target.value)} />
        <fieldset>
          <legend>For</legend>
          <div className="chips">
            {[3, 6, 12].map((n) => (
              <label key={n} className="chip">
                <input type="radio" name="months" checked={months === n} onChange={() => setMonths(n)} />
                {n} months
              </label>
            ))}
          </div>
        </fieldset>
        <ErrorNote message={action.error} />
        <button className="btn-primary" disabled={!seller || !material || !grams || !paise || action.busy}>
          Send offer
        </button>
      </form>
    </section>
  );
}
