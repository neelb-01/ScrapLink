import { useEffect, useState, type CSSProperties, type FormEvent } from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";
import { api, type Grade, type Seller } from "../api/client";
import { useUser } from "../auth";
import { AuthedImage, ErrorNote, Field, Loading, Steps, useAction, useLoad } from "../components";
import { kg, parseKg, parseRupees, perKg, rupees } from "../format";
import { metalColour } from "../lots";

/** Phone photos run to several MB; 1600px JPEG keeps detail and saves the seller's data. */
async function shrink(file: File): Promise<File> {
  try {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, 1600 / Math.max(bitmap.width, bitmap.height));
    if (scale === 1 && file.size < 1_500_000) return file;
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas.getContext("2d")!.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise<Blob | null>((done) => canvas.toBlob(done, "image/jpeg", 0.85));
    return blob ? new File([blob], "lot.jpg", { type: "image/jpeg" }) : file;
  } catch {
    return file;
  }
}

export function PhotoStep() {
  const user = useUser();
  const navigate = useNavigate();
  const [photo, setPhoto] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [seller, setSeller] = useState<Seller | null>(null);
  const [sellerPhone, setSellerPhone] = useState("");
  const lookup = useAction();
  const upload = useAction();
  const isAgent = user.role === "agent";

  useEffect(() => {
    if (!photo) return;
    const url = URL.createObjectURL(photo);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [photo]);

  const findSeller = (event: FormEvent) => {
    event.preventDefault();
    void lookup.run(async () => setSeller(await api.lookupSeller(sellerPhone.trim())));
  };

  const send = () =>
    upload.run(async () => {
      const lot = await api.createLot(await shrink(photo!), seller?.id);
      navigate(`/lots/${lot.id}/details`);
    });

  return (
    <>
      <Steps current={1} />
      <h1>Photograph the lot</h1>

      {isAgent && (
        <form onSubmit={findSeller} className="panel stack">
          <Field
            label="Seller's phone number"
            type="tel"
            inputMode="numeric"
            required
            value={sellerPhone}
            onChange={(e) => {
              setSellerPhone(e.target.value);
              setSeller(null);
            }}
          />
          <ErrorNote message={lookup.error} />
          {seller ? (
            <p className={seller.kyc_status === "approved" ? "confirmed" : "error-note"}>
              {seller.kyc_status === "approved"
                ? `Listing for ${seller.business_name ?? seller.name}`
                : `${seller.name} isn't approved to sell yet.`}
            </p>
          ) : (
            <button className="btn" disabled={lookup.busy}>
              Find seller
            </button>
          )}
        </form>
      )}

      <label className={preview ? "camera camera-filled" : "camera"}>
        {preview ? (
          <img src={preview} alt="The lot you photographed" />
        ) : (
          <span className="camera-prompt">
            <span className="camera-title">Take a photo</span>
            <span className="camera-hint">Stand back so the whole lot is in the picture, in daylight if you can.</span>
          </span>
        )}
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp"
          capture="environment"
          className="visually-hidden"
          onChange={(e) => setPhoto(e.target.files?.[0] ?? null)}
        />
      </label>
      {preview && <p className="aside">Tap the photo to take it again.</p>}

      <ErrorNote message={upload.error} />
      <button
        type="button"
        className="btn-primary"
        disabled={!photo || upload.busy || (isAgent && seller?.kyc_status !== "approved")}
        onClick={() => void send()}
      >
        {upload.busy ? "Sending photo…" : "Use this photo"}
      </button>
    </>
  );
}

export function DetailsStep() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const lot = useLoad(() => api.lot(id), [id]);
  const catalogue = useLoad(() => api.catalogue(), []);
  const [material, setMaterial] = useState<string | null>(null);
  const [grade, setGrade] = useState<Grade | null>(null);
  const [weight, setWeight] = useState("");
  const action = useAction();

  useEffect(() => {
    const l = lot.data;
    if (!l) return;
    const c = l.classification;
    setMaterial(l.material_code ?? (c.prefilled ? c.suggested_material_code : null));
    setGrade((l.grade ?? (c.prefilled ? c.suggested_grade : null)) as Grade | null);
    if (l.declared_weight_grams) setWeight(String(l.declared_weight_grams / 1000));
  }, [lot.data]);

  if (lot.error) return <ErrorNote message={lot.error} />;
  if (!lot.data || !catalogue.data) return <Loading />;
  if (lot.data.status !== "draft") return <Navigate to={`/lots/${id}`} replace />;

  const c = lot.data.classification;
  const suggested = catalogue.data.materials.find((m) => m.code === c.suggested_material_code);
  const grams = parseKg(weight);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!material || !grade || !grams) return;
    void action.run(async () => {
      await api.confirmLot(id, material, grade, grams);
      navigate(`/lots/${id}/sell`);
    });
  };

  return (
    <>
      <Steps current={2} />
      <h1>What is it?</h1>
      <AuthedImage path={lot.data.photo_url} alt="The lot" className="photo-thumb" />
      {c.prefilled && suggested ? (
        <p className="note">
          From the photo this looks like <strong>{suggested.name.toLowerCase()}</strong>. Change it if
          it's wrong: you know your material best.
        </p>
      ) : (
        <p className="note">Choose the metal. The photo didn't show it clearly enough to suggest one.</p>
      )}

      <form onSubmit={submit} className="stack">
        <fieldset>
          <legend>Metal</legend>
          <div className="metals">
            {catalogue.data.materials.map((m) => (
              <label
                key={m.code}
                className="metal"
                style={{ "--metal": metalColour(m.code) } as CSSProperties}
              >
                <input
                  type="radio"
                  name="material"
                  value={m.code}
                  checked={material === m.code}
                  onChange={() => setMaterial(m.code)}
                />
                <span className="metal-swatch" aria-hidden="true" />
                <span className="metal-name">{m.name}</span>
                <span className="metal-detail">{m.description}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend>Condition</legend>
          <div className="grades">
            {catalogue.data.grades.map((g) => (
              <label key={g.code} className="grade">
                <input
                  type="radio"
                  name="grade"
                  value={g.code}
                  checked={grade === g.code}
                  onChange={() => setGrade(g.code as Grade)}
                />
                <span className="grade-code">{g.code}</span>
                <span className="grade-label">{g.label}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <Field
          label="Weight in kg"
          inputMode="decimal"
          required
          value={weight}
          onChange={(e) => setWeight(e.target.value)}
          hint="Your best estimate. The weighbridge reading at pickup decides the final payment."
        />
        {weight && !grams && <p className="error-note">Enter the weight as a number, like 180 or 176.5</p>}

        <ErrorNote message={action.error} />
        <button className="btn-primary" disabled={!material || !grade || !grams || action.busy}>
          See the price
        </button>
      </form>
    </>
  );
}

const DURATIONS = [
  { hours: 6, label: "6 hours" },
  { hours: 12, label: "12 hours" },
  { hours: 24, label: "1 day" },
  { hours: 48, label: "2 days" },
];

export function SellStep() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const lot = useLoad(() => api.lot(id), [id]);
  const [hours, setHours] = useState(24);
  const [minimum, setMinimum] = useState("");
  const action = useAction();

  if (lot.error) return <ErrorNote message={lot.error} />;
  if (!lot.data) return <Loading />;
  const l = lot.data;
  if (l.status !== "draft") return <Navigate to={`/lots/${id}`} replace />;
  if (!l.estimate) return <Navigate to={`/lots/${id}/details`} replace />;

  const minimumPaise = minimum.trim() ? parseRupees(minimum) : null;
  const minimumInvalid = minimum.trim() !== "" && minimumPaise === null;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    void action.run(async () => {
      await api.listLot(id, hours, minimumPaise);
      navigate(`/lots/${id}`);
    });
  };

  return (
    <>
      <Steps current={3} />
      <h1>Your price</h1>
      <div className="worth" style={{ "--metal": metalColour(l.material_code) } as CSSProperties}>
        <span className="worth-label">Worth about</span>
        <span className="worth-range">
          <span className="nowrap">{rupees(l.estimate.low_paise)} –</span>{" "}
          <span className="nowrap">{rupees(l.estimate.high_paise)}</span>
        </span>
        <span className="worth-basis">
          {perKg(l.estimate.rate_paise_per_kg)} for grade {l.grade} {l.material_name?.toLowerCase()},
          on {kg(l.declared_weight_grams!)}, at today's reference price.
        </span>
      </div>
      <p className="note">Recyclers bid without seeing each other's offers. The highest bid wins.</p>

      <form onSubmit={submit} className="stack">
        <fieldset>
          <legend>Take bids for</legend>
          <div className="chips">
            {DURATIONS.map((d) => (
              <label key={d.hours} className="chip">
                <input
                  type="radio"
                  name="hours"
                  checked={hours === d.hours}
                  onChange={() => setHours(d.hours)}
                />
                <span>{d.label}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <details className="optional">
          <summary>Set a lowest price you'll accept</summary>
          <Field
            label="Lowest price per kg (₹)"
            inputMode="decimal"
            value={minimum}
            onChange={(e) => setMinimum(e.target.value)}
            hint="If no bid reaches this, the lot is not sold. Buyers don't see it."
          />
          {minimumInvalid && <p className="error-note">Enter a price like 550 or 549.50</p>}
        </details>

        <ErrorNote message={action.error} />
        <button className="btn-primary" disabled={action.busy || minimumInvalid}>
          Start taking bids
        </button>
      </form>
    </>
  );
}
