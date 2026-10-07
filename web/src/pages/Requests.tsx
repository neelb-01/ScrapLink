import { useState, type CSSProperties, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, type Material, type Rfq, type User } from "../api/client";
import { useUser } from "../auth";
import { ErrorNote, Field, Loading, useAction, useLoad } from "../components";
import { day, kg, parseKg, parseRupees, perKg, todayInput } from "../format";
import { FAMILY_NAMES, metalColour } from "../lots";

// Requests for quotation, first slice: buyers post what they need and sellers see the demand.
// Quoting against a request comes next.

export function Requests() {
  const user = useUser();
  const rfqs = useLoad(() => api.rfqs(), []);
  const title = user.role === "buyer" ? "Your requests" : "Buyer requests";

  return (
    <>
      <h1>{title}</h1>
      {user.role === "seller" && (
        <p className="lede">
          Buyers looking for material now. Have some? List it and they can bid. Quoting on a request directly is coming
          in a later release.
        </p>
      )}
      {user.role === "buyer" && <RequestForm user={user} onPosted={() => void rfqs.reload()} />}
      <ErrorNote message={rfqs.error} />
      {!rfqs.data && !rfqs.error && <Loading />}
      {rfqs.data?.length === 0 && (
        <p className="empty">
          {user.role === "buyer" ? "You haven't posted a request yet." : "No buyer is asking for anything right now."}
        </p>
      )}
      <ul className="queue">
        {rfqs.data?.map((rfq) => (
          <RequestCard key={rfq.id} rfq={rfq} user={user} onChange={() => void rfqs.reload()} />
        ))}
      </ul>
    </>
  );
}

function RequestCard({ rfq, user, onChange }: { rfq: Rfq; user: User; onChange: () => void }) {
  const action = useAction();
  const mine = rfq.buyer.id === user.id;
  return (
    <li className="panel card" style={{ "--metal": metalColour(rfq.material_code) } as CSSProperties}>
      <h2>
        {kg(rfq.quantity_grams)} of {rfq.material_name}
      </h2>
      <dl className="facts">
        {!mine && (
          <div className="fact">
            <dt>Buyer</dt>
            <dd>{rfq.buyer.business_name ?? rfq.buyer.name}</dd>
          </div>
        )}
        <div className="fact">
          <dt>Needed by</dt>
          <dd>{day(rfq.needed_by)}</dd>
        </div>
        <div className="fact">
          <dt>Target price</dt>
          <dd>{rfq.target_rate_paise_per_kg ? perKg(rfq.target_rate_paise_per_kg) : "Open to offers"}</dd>
        </div>
        {mine && (
          <div className="fact">
            <dt>Status</dt>
            <dd>{rfq.status === "open" ? "Open" : "Closed"}</dd>
          </div>
        )}
      </dl>
      {rfq.note && <p className="note">“{rfq.note}”</p>}
      <ErrorNote message={action.error} />
      {mine && rfq.status === "open" && (
        <button
          type="button"
          className="btn"
          disabled={action.busy}
          onClick={() => void action.run(async () => (await api.closeRfq(rfq.id), onChange()))}
        >
          Close request
        </button>
      )}
      {user.role === "seller" && (
        <Link to="/lots/new" className="btn">
          List a lot
        </Link>
      )}
    </li>
  );
}

export function MaterialSelect({
  materials,
  value,
  onChange,
  user,
}: {
  materials: Material[];
  value: string;
  onChange: (code: string) => void;
  user: User;
}) {
  const families = [...new Set(materials.map((m) => m.family))];
  return (
    <label className="field">
      <span className="field-label">Material</span>
      <select required value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="" disabled>
          Choose a material
        </option>
        {families.map((family) => (
          <optgroup key={family} label={FAMILY_NAMES[family] ?? family}>
            {materials
              .filter((m) => m.family === family)
              .map((m) => {
                const barred = m.authorisation !== null && !user.authorisations.includes(m.authorisation);
                return (
                  <option key={m.code} value={m.code} disabled={barred}>
                    {m.name}
                    {barred ? " (authorised recyclers only)" : ""}
                  </option>
                );
              })}
          </optgroup>
        ))}
      </select>
    </label>
  );
}

function RequestForm({ user, onPosted }: { user: User; onPosted: () => void }) {
  const catalogue = useLoad(() => api.catalogue(), []);
  const [material, setMaterial] = useState("");
  const [quantity, setQuantity] = useState("");
  const [target, setTarget] = useState("");
  const [neededBy, setNeededBy] = useState(() => todayInput(7));
  const [note, setNote] = useState("");
  const action = useAction();
  const grams = parseKg(quantity);
  const paise = target ? parseRupees(target) : null;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!material || !grams) return;
    void action.run(async () => {
      await api.postRfq({
        material_code: material,
        quantity_grams: grams,
        target_rate_paise_per_kg: paise,
        // The end of the chosen day, where the buyer is.
        needed_by: new Date(`${neededBy}T23:59`).toISOString(),
        note,
      });
      setMaterial("");
      setQuantity("");
      setTarget("");
      setNote("");
      onPosted();
    });
  };

  return (
    <section className="panel">
      <h2>Ask for a material</h2>
      <p className="note">Sellers see your request with your business name. They don't see your other trades.</p>
      {!catalogue.data ? (
        <Loading />
      ) : (
        <form className="stack" onSubmit={submit}>
          <MaterialSelect materials={catalogue.data.materials} value={material} onChange={setMaterial} user={user} />
          <Field label="Quantity in kg" inputMode="decimal" required value={quantity} onChange={(e) => setQuantity(e.target.value)} />
          <Field
            label="Target price per kg (₹, optional)"
            inputMode="decimal"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
          />
          <Field
            label="Needed by"
            type="date"
            required
            min={todayInput(1)}
            value={neededBy}
            onChange={(e) => setNeededBy(e.target.value)}
          />
          <Field label="Note for sellers (optional)" maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} />
          <ErrorNote message={action.error} />
          <button className="btn-primary" disabled={!material || !grams || (target !== "" && !paise) || action.busy}>
            Post request
          </button>
        </form>
      )}
    </section>
  );
}
