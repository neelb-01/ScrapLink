import { useState, type CSSProperties, type FormEvent } from "react";
import { api, type Authorisation, type Material, type User } from "../api/client";
import { ErrorNote, Loading, useAction, useLoad } from "../components";
import { day, parseRupees, perKg, when } from "../format";
import { AUTHORISATION_NAMES, metalColour, rateReason, rateSource } from "../lots";

const ROLE_NAMES: Record<string, string> = { seller: "Seller", buyer: "Buyer" };

export function Approvals() {
  const pending = useLoad(() => api.users("pending"), []);
  return (
    <>
      <h1>Approvals</h1>
      <p className="lede">
        Format and checksum are already verified. Confirm the GSTIN on the GST portal before approving a buyer.
      </p>
      <ErrorNote message={pending.error} />
      {!pending.data && !pending.error && <Loading />}
      {pending.data?.length === 0 && <p className="empty">Nobody is waiting for approval.</p>}
      <ul className="queue">
        {pending.data?.map((u) => (
          <Applicant key={u.id} user={u} onDone={() => void pending.reload()} />
        ))}
      </ul>
    </>
  );
}

function Applicant({ user, onDone }: { user: User; onDone: () => void }) {
  const [rejecting, setRejecting] = useState(false);
  const [note, setNote] = useState("");
  const [held, setHeld] = useState<Authorisation[]>([]);
  const action = useAction();
  const decide = (decision: "approve" | "reject") =>
    action.run(async () => {
      await api.decideKyc(user.id, decision, note, held);
      onDone();
    });
  const toggle = (code: Authorisation) =>
    setHeld(held.includes(code) ? held.filter((c) => c !== code) : [...held, code]);

  return (
    <li className="panel">
      <h2>
        {user.name}
        {user.business_name && <span className="subtle">, {user.business_name}</span>}
      </h2>
      <dl className="facts">
        <div className="fact">
          <dt>Role</dt>
          <dd>{ROLE_NAMES[user.role] ?? user.role}</dd>
        </div>
        <div className="fact">
          <dt>Phone</dt>
          <dd>{user.phone}</dd>
        </div>
        {user.gstin && (
          <div className="fact">
            <dt>GSTIN</dt>
            <dd>{user.gstin}</dd>
          </div>
        )}
        {user.pan && (
          <div className="fact">
            <dt>PAN</dt>
            <dd>{user.pan}</dd>
          </div>
        )}
      </dl>
      {user.role === "buyer" && !rejecting && (
        <fieldset className="authorisations">
          <legend>Authorisations seen (needed to buy e-waste or batteries)</legend>
          {(Object.keys(AUTHORISATION_NAMES) as Authorisation[]).map((code) => (
            <label key={code} className="check">
              <input type="checkbox" checked={held.includes(code)} onChange={() => toggle(code)} />
              {AUTHORISATION_NAMES[code]}
            </label>
          ))}
        </fieldset>
      )}
      <ErrorNote message={action.error} />
      {rejecting ? (
        <form
          className="stack"
          onSubmit={(e) => {
            e.preventDefault();
            void decide("reject");
          }}
        >
          <label className="field">
            <span className="field-label">Reason, shown to the applicant</span>
            <textarea required value={note} onChange={(e) => setNote(e.target.value)} />
          </label>
          <div className="row">
            <button className="btn-danger" disabled={action.busy}>
              Reject
            </button>
            <button type="button" className="btn" onClick={() => setRejecting(false)}>
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <div className="row">
          <button type="button" className="btn-primary" disabled={action.busy} onClick={() => void decide("approve")}>
            Approve
          </button>
          <button type="button" className="btn" onClick={() => setRejecting(true)}>
            Reject
          </button>
        </div>
      )}
    </li>
  );
}

export function Prices() {
  const catalogue = useLoad(() => api.catalogue(), []);
  return (
    <>
      <h1>Reference prices</h1>
      <p className="lede">
        The grade A price per kg. Grade B lots are valued at 85% of it and grade C at 65%. A change applies to lots
        confirmed from now on.
      </p>
      {catalogue.data && (
        <p className="note">
          Each night a price moves {catalogue.data.pricing_rule.blend_percent}% of the way toward the middle price of
          the paid trades of the past {catalogue.data.pricing_rule.window_days} days, by at most{" "}
          {catalogue.data.pricing_rule.max_step_percent}%. It holds until there are{" "}
          {catalogue.data.pricing_rule.min_trades} such trades. A price you set here starts it again from your figure.
        </p>
      )}
      <ErrorNote message={catalogue.error} />
      {!catalogue.data && !catalogue.error && <Loading />}
      <ul className="queue">
        {catalogue.data?.materials.map((m) => (
          <PriceRow key={m.code} material={m} onSaved={() => void catalogue.reload()} />
        ))}
      </ul>
    </>
  );
}

function PriceRow({ material, onSaved }: { material: Material; onSaved: () => void }) {
  const [value, setValue] = useState("");
  const [showHistory, setShowHistory] = useState(false);
  const action = useAction();
  const paise = parseRupees(value);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!paise) return;
    void action.run(async () => {
      await api.setRate(material.code, paise);
      setValue("");
      onSaved();
    });
  };

  return (
    <li className="panel price-row" style={{ "--metal": metalColour(material.code) } as CSSProperties}>
      <span className="metal-swatch" aria-hidden="true" />
      <div>
        <h2>{material.name}</h2>
        <p>
          {material.reference_rate_paise_per_kg ? perKg(material.reference_rate_paise_per_kg) : "No price set"}
          {material.rate_effective_from && <span className="subtle"> since {when(material.rate_effective_from)}</span>}
        </p>
        {material.rate && <p className="subtle">{rateReason(material.rate)}</p>}
      </div>
      <form onSubmit={submit} className="price-form">
        <label className="visually-hidden" htmlFor={`rate-${material.code}`}>
          New price per kg for {material.name}
        </label>
        <input
          id={`rate-${material.code}`}
          inputMode="decimal"
          placeholder="New ₹/kg"
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
        <button className="btn" disabled={!paise || action.busy}>
          Update
        </button>
      </form>
      <ErrorNote message={action.error} />
      <details className="optional" onToggle={(e) => setShowHistory(e.currentTarget.open)}>
        <summary>Price history</summary>
        {showHistory && <RateHistory code={material.code} version={material.rate_effective_from} />}
      </details>
    </li>
  );
}

function RateHistory({ code, version }: { code: string; version: string | null }) {
  const rates = useLoad(() => api.rates(code), [code, version]);
  if (rates.error) return <ErrorNote message={rates.error} />;
  if (!rates.data) return <Loading />;
  return (
    <ul className="rate-history">
      {rates.data.map((r, i) => (
        <li key={i}>
          <span>{day(r.effective_from)}</span>
          <strong>{perKg(r.rate_paise_per_kg)}</strong>
          <span className="subtle">{rateSource(r)}</span>
        </li>
      ))}
    </ul>
  );
}
