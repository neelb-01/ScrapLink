import { useState, type CSSProperties, type FormEvent } from "react";
import { api, type Material, type User } from "../api/client";
import { ErrorNote, Loading, useAction, useLoad } from "../components";
import { parseRupees, perKg, when } from "../format";
import { metalColour } from "../lots";

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
  const action = useAction();
  const decide = (decision: "approve" | "reject") =>
    action.run(async () => {
      await api.decideKyc(user.id, decision, note);
      onDone();
    });

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
    </li>
  );
}
