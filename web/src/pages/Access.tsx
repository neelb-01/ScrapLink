import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, type RegisterIn } from "../api/client";
import { useAuth } from "../auth";
import { ErrorNote, Field, useAction } from "../components";

export function SignIn() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const action = useAction();

  const submit = (event: FormEvent) => {
    event.preventDefault();
    void action.run(async () => {
      await signIn(phone.trim(), password);
      navigate("/");
    });
  };

  return (
    <div className="access">
      <h1 className="brand-large">ScrapLink</h1>
      <p className="lede">Sell scrap metal at a fair price, and get paid safely.</p>
      <form onSubmit={submit} className="stack">
        <Field
          label="Phone number"
          type="tel"
          inputMode="numeric"
          autoComplete="tel"
          required
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
        />
        <Field
          label="Password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <ErrorNote message={action.error} />
        <button className="btn-primary" disabled={action.busy}>
          Sign in
        </button>
      </form>
      <p className="aside">
        New to ScrapLink? <Link to="/register">Create an account</Link>
      </p>
    </div>
  );
}

const ROLES = [
  { role: "seller", title: "I sell scrap", detail: "Dealers, workshops, factories" },
  { role: "buyer", title: "I buy scrap", detail: "Recyclers and smelters. GSTIN needed" },
] as const;

export function Register() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [role, setRole] = useState<RegisterIn["role"] | null>(null);
  const [form, setForm] = useState({ name: "", phone: "", password: "", business: "", gstin: "", pan: "" });
  const action = useAction();
  const set = (key: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm({ ...form, [key]: e.target.value });

  if (!role) {
    return (
      <div className="access">
        <h1 className="brand-large">ScrapLink</h1>
        <h2>What do you do?</h2>
        <div className="choices">
          {ROLES.map((r) => (
            <button key={r.role} type="button" className="choice" onClick={() => setRole(r.role)}>
              <span className="choice-title">{r.title}</span>
              <span className="choice-detail">{r.detail}</span>
            </button>
          ))}
        </div>
        <p className="aside">
          Already registered? <Link to="/signin">Sign in</Link>
        </p>
      </div>
    );
  }

  const submit = (event: FormEvent) => {
    event.preventDefault();
    void action.run(async () => {
      await api.register({
        role,
        name: form.name.trim(),
        phone: form.phone.trim(),
        password: form.password,
        business_name: form.business.trim() || null,
        gstin: form.gstin.trim() || null,
        pan: form.pan.trim() || null,
      });
      await signIn(form.phone.trim(), form.password);
      navigate("/");
    });
  };

  return (
    <div className="access">
      <button type="button" className="btn-quiet back" onClick={() => setRole(null)}>
        Back
      </button>
      <h2>{ROLES.find((r) => r.role === role)?.title}</h2>
      <form onSubmit={submit} className="stack">
        <Field label="Your name" required autoComplete="name" value={form.name} onChange={set("name")} />
        <Field
          label="Phone number"
          type="tel"
          inputMode="numeric"
          required
          autoComplete="tel"
          value={form.phone}
          onChange={set("phone")}
        />
        <Field
          label="Password"
          type="password"
          required
          minLength={8}
          autoComplete="new-password"
          hint="At least 8 characters"
          value={form.password}
          onChange={set("password")}
        />
        <Field label="Business name" value={form.business} onChange={set("business")} />
        {role === "buyer" && (
          <Field
            label="GSTIN"
            required
            autoCapitalize="characters"
            hint="15 characters, as on your GST certificate"
            value={form.gstin}
            onChange={set("gstin")}
          />
        )}
        {role === "seller" && (
          <>
            <Field
              label="GSTIN (if registered)"
              autoCapitalize="characters"
              value={form.gstin}
              onChange={set("gstin")}
            />
            <Field label="PAN" autoCapitalize="characters" value={form.pan} onChange={set("pan")} />
          </>
        )}
        <ErrorNote message={action.error} />
        <button className="btn-primary" disabled={action.busy}>
          Create account
        </button>
      </form>
    </div>
  );
}

export function AwaitingApproval({ rejected, note }: { rejected: boolean; note: string | null }) {
  const { signOut, refresh } = useAuth();
  return (
    <div className="access">
      <h1 className="brand-large">ScrapLink</h1>
      {rejected ? (
        <>
          <h2>Your account was not approved</h2>
          <p>{note ?? "Contact ScrapLink support to find out why and what to send."}</p>
        </>
      ) : (
        <>
          <h2>We're checking your details</h2>
          <p>
            Before anyone can trade, ScrapLink confirms their business details. This usually takes a
            working day. You can sign in again later, or check now.
          </p>
        </>
      )}
      <div className="row">
        {!rejected && (
          <button type="button" className="btn-primary" onClick={() => void refresh()}>
            Check again
          </button>
        )}
        <button type="button" className="btn" onClick={signOut}>
          Sign out
        </button>
      </div>
    </div>
  );
}
