import { useState, type FormEvent } from "react";
import { api } from "../api/client";
import { useAuth, useUser } from "../auth";
import { ErrorNote, Field, SelectField, useAction, usePlaces } from "../components";

const ROLE_NAMES: Record<string, string> = { seller: "Seller", buyer: "Buyer", admin: "Admin" };
const KYC_TEXT: Record<string, string> = {
  pending: "Being checked",
  approved: "Approved",
  rejected: "Not approved",
};

/** Upload or replace the KYC or licence document an admin checks before approving. */
export function KycDocument() {
  const { user, refresh } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const action = useAction();
  if (!user) return null;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!file) return;
    void action.run(async () => {
      await api.uploadKycDocument(file);
      await refresh();
      setFile(null);
    });
  };

  return (
    <form className="stack" onSubmit={submit}>
      <p>
        {user.kyc_document_name ? (
          <>
            Uploaded: <strong>{user.kyc_document_name}</strong>. You can replace it.
          </>
        ) : (
          "Upload your GST certificate, trade licence or, for e-waste and battery buyers, your CPCB authorisation."
        )}
      </p>
      <label className="field">
        <span className="field-label">Document (PDF or photo, up to 10 MB)</span>
        <input
          type="file"
          accept="application/pdf,image/jpeg,image/png,image/webp"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
      </label>
      <ErrorNote message={action.error} />
      <button className="btn" disabled={!file || action.busy}>
        {action.busy ? "Uploading…" : "Upload document"}
      </button>
    </form>
  );
}

export function Profile() {
  const user = useUser();
  const { refresh } = useAuth();
  const places = usePlaces();
  const [business, setBusiness] = useState(user.business_name ?? "");
  const [email, setEmail] = useState(user.email ?? "");
  const [place, setPlace] = useState(user.place ?? "");
  const [saved, setSaved] = useState(false);
  const action = useAction();

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setSaved(false);
    void action.run(async () => {
      await api.updateProfile({
        business_name: business.trim() || null,
        email: email.trim() || null,
        place: place || null,
      });
      await refresh();
      setSaved(true);
    });
  };

  return (
    <>
      <h1>Your business</h1>
      <section className="panel">
        <h2>Profile</h2>
        <form className="stack" onSubmit={submit}>
          <Field label="Business name" value={business} onChange={(e) => setBusiness(e.target.value)} />
          <Field
            label="Email (optional)"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            hint="Updates about your trades are emailed here as well as shown in the app."
          />
          <SelectField label="Town" value={place} onChange={(e) => setPlace(e.target.value)}>
            <option value="">Not set</option>
            {places.map((p) => (
              <option key={p.code} value={p.code}>
                {p.name}, {p.state}
              </option>
            ))}
          </SelectField>
          <ErrorNote message={action.error} />
          {saved && <p className="confirmed">Saved.</p>}
          <button className="btn-primary" disabled={action.busy}>
            Save
          </button>
        </form>
      </section>

      <section className="panel">
        <h2>KYC</h2>
        <dl className="facts">
          <div className="fact">
            <dt>Account</dt>
            <dd>{ROLE_NAMES[user.role] ?? user.role}</dd>
          </div>
          <div className="fact">
            <dt>Status</dt>
            <dd>{KYC_TEXT[user.kyc_status] ?? user.kyc_status}</dd>
          </div>
          {user.gstin && (
            <div className="fact fact-wide">
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
        <p className="note">GSTIN and PAN can't be changed here once checked. Contact ScrapLink support to correct them.</p>
        {user.role !== "admin" && <KycDocument />}
      </section>
    </>
  );
}
