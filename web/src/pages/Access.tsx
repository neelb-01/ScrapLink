import { useState, type CSSProperties, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, type RegisterIn } from "../api/client";
import { useAuth } from "../auth";
import { ErrorNote, Field, PasswordField, useAction } from "../components";
import { ThemeToggle } from "../theme";

/** The four things a newcomer needs to trust before they trade, in the order they happen. */
const HOW_IT_WORKS = [
  {
    metal: "var(--copper)",
    title: "Photograph the lot",
    detail: "Choose the material and weight, and see a fair price range from today's rates.",
  },
  {
    metal: "var(--brass)",
    title: "Recyclers bid, sealed",
    detail: "Approved buyers bid without seeing each other's offers. The highest bid wins.",
  },
  {
    metal: "var(--aluminium)",
    title: "Money waits in escrow",
    detail: "The buyer pays before pickup. The seller is paid on the weighbridge weight.",
  },
  {
    metal: "var(--steel)",
    title: "A certificate for every trade",
    detail: "Each step is recorded, and anyone can check that the certificate is genuine.",
  },
];

/**
 * Signed-out pages share one frame. On a phone the brand band sits above the form and the
 * explanation follows it; on a wide screen the brand and explanation take the left column.
 */
function AccessFrame({ children }: { children: ReactNode }) {
  return (
    <div className="access-frame">
      <header className="access-intro">
        <div className="access-top">
          <span className="wordmark">ScrapLink</span>
          <ThemeToggle />
        </div>
        <p className="access-pitch">Fair prices for scrap metal. Safe payment for both sides.</p>
      </header>
      <main className="access-main">
        <div className="access-panel">{children}</div>
      </main>
      <section className="access-how" aria-labelledby="how-title">
        <h2 id="how-title">How a trade works</h2>
        <ol className="how">
          {HOW_IT_WORKS.map((step) => (
            <li key={step.title} style={{ "--metal": step.metal } as CSSProperties}>
              <span className="how-plate" aria-hidden="true" />
              <span className="how-title">{step.title}</span>
              <span className="how-detail">{step.detail}</span>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}

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
    <AccessFrame>
      <h1>Sign in</h1>
      <form onSubmit={submit} className="stack">
        <Field
          label="Phone number"
          type="tel"
          inputMode="numeric"
          autoComplete="tel"
          required
          hint="The number you registered with"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
        />
        <PasswordField
          label="Password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <ErrorNote message={action.error} />
        <button className="btn-primary" disabled={action.busy}>
          {action.busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <div className="access-alt">
        <p>New to ScrapLink?</p>
        <Link to="/register" className="btn">
          Create an account
        </Link>
      </div>
    </AccessFrame>
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
      <AccessFrame>
        <h1>What do you do?</h1>
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
      </AccessFrame>
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
    <AccessFrame>
      <button type="button" className="btn-quiet back" onClick={() => setRole(null)}>
        Back
      </button>
      <h1>{ROLES.find((r) => r.role === role)?.title}</h1>
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
        <PasswordField
          label="Password"
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
    </AccessFrame>
  );
}

export function AwaitingApproval({ rejected, note }: { rejected: boolean; note: string | null }) {
  const { signOut, refresh } = useAuth();
  return (
    <AccessFrame>
      {rejected ? (
        <>
          <h1>Your account was not approved</h1>
          <p>{note ?? "Contact ScrapLink support to find out why and what to send."}</p>
        </>
      ) : (
        <>
          <h1>We're checking your details</h1>
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
    </AccessFrame>
  );
}
