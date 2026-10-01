import {
  useCallback,
  useEffect,
  useId,
  useState,
  type CSSProperties,
  type DependencyList,
  type InputHTMLAttributes,
  type ReactNode,
} from "react";
import { Link } from "react-router-dom";
import { ApiError, fetchBlob, type Lot, type User } from "./api/client";
import { kg, perKg, rupees } from "./format";
import { metalColour, statusFor } from "./lots";

export function useLoad<T>(load: () => Promise<T>, deps: DependencyList) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const run = useCallback(load, deps);

  const reload = useCallback(async () => {
    try {
      setData(await run());
      setError(null);
    } catch (err) {
      setError(messageOf(err));
    }
  }, [run]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { data, error, reload, setData };
}

export function messageOf(err: unknown): string {
  return err instanceof ApiError ? err.message : "Something went wrong. Try again.";
}

/** Wraps an async action with a busy flag and an error message. */
export function useAction() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const run = useCallback(async (action: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setBusy(false);
    }
  }, []);
  return { busy, error, run, setError };
}

export function ErrorNote({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p className="error-note" role="alert">
      {message}
    </p>
  );
}

export function Loading() {
  return <p className="loading">Loading…</p>;
}

export function Field({
  label,
  hint,
  ...input
}: { label: string; hint?: ReactNode } & InputHTMLAttributes<HTMLInputElement>) {
  const id = useId();
  // The hint is linked, not nested: inside the <label> it would become part of the field's name.
  return (
    <div className="field">
      <label className="field-label" htmlFor={id}>
        {label}
      </label>
      <input id={id} aria-describedby={hint ? `${id}-hint` : undefined} {...input} />
      {hint && (
        <span className="field-hint" id={`${id}-hint`}>
          {hint}
        </span>
      )}
    </div>
  );
}

export function AuthedImage({ path, alt, className }: { path: string; alt: string; className?: string }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;
    fetchBlob(path)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch(() => setUrl(null));
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [path]);
  const classes = ["photo", className].filter(Boolean).join(" ");
  return url ? (
    <img src={url} alt={alt} className={classes} />
  ) : (
    <div className={`${classes} photo-empty`} role="img" aria-label={alt} />
  );
}

function priceLine(lot: Lot): string {
  if (lot.settled_amount_paise != null) return `Paid ${rupees(lot.settled_amount_paise)}`;
  if (lot.award) return perKg(lot.award.rate_paise_per_kg);
  if (lot.estimate) return `${rupees(lot.estimate.low_paise)} – ${rupees(lot.estimate.high_paise)}`;
  return "";
}

/** A lot drawn as the stamped tag dealers hang on a bundle, in the colour of its metal. */
export function LotTag({ lot, user }: { lot: Lot; user: User }) {
  const status = statusFor(lot, user);
  const grams = lot.measured_weight_grams ?? lot.declared_weight_grams;
  return (
    <Link
      to={`/lots/${lot.id}`}
      className="tag"
      style={{ "--metal": metalColour(lot.material_code) } as CSSProperties}
    >
      <span className="tag-hole" aria-hidden="true" />
      <span className="tag-body">
        <span className="tag-metal">
          {lot.material_name ?? "Metal not chosen yet"}
          {lot.grade && <span className="tag-grade">Grade {lot.grade}</span>}
        </span>
        <span className="tag-figures">
          <span className="tag-weight">{grams ? kg(grams) : "Weight not entered"}</span>
          <span className="tag-price">{priceLine(lot)}</span>
        </span>
        <span className={`status status-${status.tone}`}>{status.text}</span>
      </span>
    </Link>
  );
}

export function Steps({ current }: { current: 1 | 2 | 3 }) {
  const names = ["Photo", "Details", "Sell"];
  return (
    <ol className="steps" aria-label="Listing steps">
      {names.map((name, i) => (
        <li
          key={name}
          className={i + 1 === current ? "step-now" : i + 1 < current ? "step-done" : undefined}
          aria-current={i + 1 === current ? "step" : undefined}
        >
          <span className="step-number">{i + 1}</span> {name}
        </li>
      ))}
    </ol>
  );
}
