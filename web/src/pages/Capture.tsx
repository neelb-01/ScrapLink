import { useEffect, useState, type CSSProperties, type FormEvent } from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";
import { api, type AuctionFormat, type Grade, type Material } from "../api/client";
import { useUser } from "../auth";
import {
  AuthedImage,
  ErrorNote,
  Field,
  Loading,
  SelectField,
  Steps,
  useAction,
  useLoad,
  usePlaces,
} from "../components";
import { kg, parseKg, parseRupees, perKg, rupees, todayInput } from "../format";
import { AUTHORISATION_NAMES, FAMILY_NAMES, metalColour, rateReason } from "../lots";

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
  const navigate = useNavigate();
  const [photo, setPhoto] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const upload = useAction();

  useEffect(() => {
    if (!photo) return;
    const url = URL.createObjectURL(photo);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [photo]);

  const send = () =>
    upload.run(async () => {
      const lot = await api.createLot(await shrink(photo!));
      navigate(`/lots/${lot.id}/details`);
    });

  return (
    <>
      <Steps current={1} />
      <h1>Photograph the lot</h1>

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
        disabled={!photo || upload.busy}
        onClick={() => void send()}
      >
        {upload.busy ? "Sending photo…" : "Use this photo"}
      </button>
    </>
  );
}

/** The catalogue in its served order, split into runs of one family each. */
function families(materials: Material[]): [string, Material[]][] {
  const groups: [string, Material[]][] = [];
  for (const m of materials) {
    const last = groups[groups.length - 1];
    if (last && last[0] === m.family) last[1].push(m);
    else groups.push([m.family, [m]]);
  }
  return groups;
}

export function DetailsStep() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const user = useUser();
  const lot = useLoad(() => api.lot(id), [id]);
  const catalogue = useLoad(() => api.catalogue(), []);
  const places = usePlaces();
  const [material, setMaterial] = useState<string | null>(null);
  const [grade, setGrade] = useState<Grade | null>(null);
  const [weight, setWeight] = useState("");
  const [place, setPlace] = useState(user.place ?? "");
  const [readyOn, setReadyOn] = useState("");
  const action = useAction();

  useEffect(() => {
    const l = lot.data;
    if (!l) return;
    const c = l.classification;
    setMaterial(l.material_code ?? (c.prefilled ? c.suggested_material_code : null));
    setGrade((l.grade ?? (c.grade_prefilled ? c.suggested_grade : null)) as Grade | null);
    if (l.declared_weight_grams) setWeight(String(l.declared_weight_grams / 1000));
    if (l.place) setPlace(l.place);
    if (l.pickup_ready_on) setReadyOn(l.pickup_ready_on);
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
      await api.confirmLot(id, {
        material_code: material,
        grade,
        declared_weight_grams: grams,
        place: place || null,
        pickup_ready_on: readyOn || null,
      });
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
        <p className="note">Choose the material. The photo didn't show it clearly enough to suggest one.</p>
      )}

      <form onSubmit={submit} className="stack">
        <fieldset>
          <legend>Material</legend>
          {families(catalogue.data.materials).map(([family, materials]) => (
            <div key={family} className="family">
              <h2 className="family-name">{FAMILY_NAMES[family] ?? family}</h2>
              <div className="metals">
                {materials.map((m) => (
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
                    <span className="metal-detail">
                      {m.description}
                      {m.authorisation && (
                        <span className="regulated"> Sold only to {AUTHORISATION_NAMES[m.authorisation]} holders.</span>
                      )}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          ))}
        </fieldset>

        <fieldset>
          <legend>Condition</legend>
          {c.suggested_grade && c.grade_confidence != null && (
            <p className="note">
              {c.grade_prefilled
                ? `From the photo it looks like grade ${c.suggested_grade}. Check it against the descriptions.`
                : `The photo hints at grade ${c.suggested_grade}, but only ${Math.round(c.grade_confidence * 100)}% sure. Choose what matches.`}
            </p>
          )}
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

        <SelectField
          label="Where is it?"
          value={place}
          onChange={(e) => setPlace(e.target.value)}
          hint="The nearest town. Buyers see it, and the price allows for the distance a truck must travel."
        >
          <option value="">Choose a town</option>
          {places.map((p) => (
            <option key={p.code} value={p.code}>
              {p.name}
              {p.km_from_yard > 0 ? ` (${p.km_from_yard} km from the yard)` : " (at the yard)"}
            </option>
          ))}
        </SelectField>

        <Field
          label="Ready for pickup from (optional)"
          type="date"
          min={todayInput()}
          value={readyOn}
          onChange={(e) => setReadyOn(e.target.value)}
          hint="The first day a truck can collect it. Leave it empty if it's ready now."
        />

        <ErrorNote message={action.error} />
        <button className="btn-primary" disabled={!material || !grade || !grams || action.busy}>
          See the price
        </button>
      </form>
    </>
  );
}

const FORMATS: { value: AuctionFormat; title: string; detail: string }[] = [
  {
    value: "sealed",
    title: "Sealed bids",
    detail: "Buyers can't see each other's offers. When bidding closes, the highest bid wins.",
  },
  {
    value: "open",
    title: "Open bidding",
    detail: "Everyone sees the best bid and must beat it. You can accept a bid before it closes.",
  },
];

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
  const [format, setFormat] = useState<AuctionFormat>("sealed");
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
      await api.listLot(id, hours, minimumPaise, format);
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
        {l.estimate.reference_rate && (
          <span className="worth-why">{rateReason(l.estimate.reference_rate)}</span>
        )}
        {l.estimate.place_name && (
          <span className="worth-why">
            {l.estimate.location_adjustment_bp
              ? `Includes a ${l.estimate.location_adjustment_bp / 100}% freight allowance: ${l.estimate.place_name} is ${l.estimate.km_from_yard} km from the yard.`
              : `${l.estimate.place_name} is at the yard, so there is no freight allowance.`}
          </span>
        )}
      </div>

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

        <fieldset>
          <legend>How buyers bid</legend>
          <div className="choices">
            {FORMATS.map((f) => (
              <label key={f.value} className="choice-row">
                <input
                  type="radio"
                  name="format"
                  checked={format === f.value}
                  onChange={() => setFormat(f.value)}
                />
                <span>
                  <span className="choice-title">{f.title}</span>
                  <span className="choice-detail">{f.detail}</span>
                </span>
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
