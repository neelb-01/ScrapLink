import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, type Anchor, type Job, type Route } from "../api/client";
import { ErrorNote, Field, Loading, useAction, useLoad } from "../components";
import { kg, km, parseKg, todayInput, when } from "../format";

// Admin operations. Each screen is the first slice of its module: enough to see it working.

// --- Transporters -------------------------------------------------------------------------

export function Transporters() {
  const transporters = useLoad(() => api.transporters(), []);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [vehicle, setVehicle] = useState("");
  const [capacity, setCapacity] = useState("");
  const action = useAction();
  const grams = parseKg(capacity);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!grams) return;
    void action.run(async () => {
      await api.addTransporter({ name, phone, vehicle, capacity_grams: grams });
      setName("");
      setPhone("");
      setVehicle("");
      setCapacity("");
      await transporters.reload();
    });
  };

  return (
    <>
      <h1>Transporters</h1>
      <p className="lede">Logistics partners who collect lots. Sending one to a booked pickup comes next.</p>
      <ErrorNote message={transporters.error} />
      {!transporters.data && !transporters.error && <Loading />}
      {transporters.data?.length === 0 && <p className="empty">No transporters added yet.</p>}
      <ul className="queue">
        {transporters.data?.map((t) => (
          <li key={t.id} className="panel">
            <h2>{t.name}</h2>
            <dl className="facts">
              <div className="fact">
                <dt>Vehicle</dt>
                <dd>{t.vehicle}</dd>
              </div>
              <div className="fact">
                <dt>Carries up to</dt>
                <dd>{kg(t.capacity_grams)}</dd>
              </div>
              <div className="fact">
                <dt>Phone</dt>
                <dd>
                  <a href={`tel:${t.phone}`}>{t.phone}</a>
                </dd>
              </div>
            </dl>
          </li>
        ))}
      </ul>
      <section className="panel">
        <h2>Add a transporter</h2>
        <form className="stack" onSubmit={submit}>
          <Field label="Name" required value={name} onChange={(e) => setName(e.target.value)} />
          <Field label="Phone number" type="tel" required value={phone} onChange={(e) => setPhone(e.target.value)} />
          <Field
            label="Vehicle"
            required
            placeholder="Tata Ace, KL-07-AB-1234"
            value={vehicle}
            onChange={(e) => setVehicle(e.target.value)}
          />
          <Field
            label="Carries up to (kg)"
            inputMode="decimal"
            required
            value={capacity}
            onChange={(e) => setCapacity(e.target.value)}
          />
          <ErrorNote message={action.error} />
          <button className="btn-primary" disabled={!grams || action.busy}>
            Add transporter
          </button>
        </form>
      </section>
    </>
  );
}

// --- Pickup routes ------------------------------------------------------------------------

function directionsUrl(route: Route): string {
  const point = (p: { latitude: number; longitude: number }) => `${p.latitude},${p.longitude}`;
  const params = new URLSearchParams({
    api: "1",
    origin: point(route.depot),
    destination: point(route.depot),
    waypoints: route.stops.map((s) => point(s.location!)).join("|"),
  });
  return `https://www.google.com/maps/dir/?${params}`;
}

export function PickupRoutes() {
  const [date, setDate] = useState(() => todayInput());
  const route = useLoad(() => api.route(date), [date]);
  const r = route.data;

  return (
    <>
      <h1>Pickup routes</h1>
      <p className="lede">
        The day's booked pickups, nearest next from the yard. A suggested order by straight-line distance, not yet an
        optimised route by road.
      </p>
      <Field label="Day" type="date" value={date} onChange={(e) => setDate(e.target.value || todayInput())} />
      <ErrorNote message={route.error} />
      {!r && !route.error && <Loading />}
      {r && r.stops.length === 0 && r.unplaced.length === 0 && (
        <p className="empty">No pickups are booked for {date}.</p>
      )}
      {r && r.stops.length > 0 && (
        <section className="panel" aria-labelledby="stops">
          <h2 id="stops">
            {r.stops.length} {r.stops.length === 1 ? "stop" : "stops"}, about {km(r.total_metres)} there and back
          </h2>
          <ol className="stops">
            {r.stops.map((stop) => (
              <li key={stop.lot_id}>
                <Link to={`/lots/${stop.lot_id}`}>{stop.seller.business_name ?? stop.seller.name}</Link>
                <span className="subtle">
                  {" "}
                  {stop.material_name}, {when(stop.pickup_at)}, {km(stop.leg_metres!)} from the last stop
                </span>
              </li>
            ))}
          </ol>
          <p className="subtle">Then {km(r.return_metres)} back to the yard.</p>
          <a className="btn" href={directionsUrl(r)} target="_blank" rel="noreferrer">
            Open in Google Maps
          </a>
        </section>
      )}
      {r && r.unplaced.length > 0 && (
        <section className="panel panel-held" aria-labelledby="unplaced">
          <h2 id="unplaced">No location given</h2>
          <p>These pickups were booked without a location, so they aren't on the route. Call to fit them in.</p>
          <ul>
            {r.unplaced.map((stop) => (
              <li key={stop.lot_id}>
                <Link to={`/lots/${stop.lot_id}`}>{stop.seller.business_name ?? stop.seller.name}</Link>{" "}
                <span className="subtle">{when(stop.pickup_at)}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}

// --- Custody anchors ----------------------------------------------------------------------

export function Anchors() {
  const anchors = useLoad(() => api.anchors(), []);
  const action = useAction();

  return (
    <>
      <h1>Record anchors</h1>
      <p className="lede">
        Each anchor seals every custody event since the one before under a single fingerprint (a Merkle root). If any
        sealed event is changed later, its anchor no longer checks out. Publishing these fingerprints outside ScrapLink
        comes next.
      </p>
      <ErrorNote message={action.error ?? anchors.error} />
      <button
        type="button"
        className="btn-primary"
        disabled={action.busy}
        onClick={() => void action.run(async () => (await api.sealAnchor(), await anchors.reload()))}
      >
        Seal new events
      </button>
      {!anchors.data && !anchors.error && <Loading />}
      {anchors.data?.length === 0 && <p className="empty">Nothing has been sealed yet.</p>}
      <ul className="queue">
        {anchors.data?.map((a) => <AnchorRow key={a.id} anchor={a} />)}
      </ul>
    </>
  );
}

function AnchorRow({ anchor }: { anchor: Anchor }) {
  const [holds, setHolds] = useState<boolean | null>(null);
  const action = useAction();
  return (
    <li className="panel">
      <h2>Anchor {anchor.id}</h2>
      <p>
        {anchor.event_count} {anchor.event_count === 1 ? "event" : "events"}, sealed {when(anchor.created_at)}
      </p>
      <p className="hash">{anchor.merkle_root}</p>
      <ErrorNote message={action.error} />
      <div className="row">
        <button
          type="button"
          className="btn"
          disabled={action.busy}
          onClick={() => void action.run(async () => setHolds((await api.checkAnchor(anchor.id)).holds))}
        >
          Check
        </button>
        {holds === true && <p className="confirmed">Every sealed event is unchanged.</p>}
        {holds === false && (
          <p className="error-note" role="alert">
            A sealed event has been changed or removed.
          </p>
        )}
      </div>
    </li>
  );
}

// --- Scheduled jobs -----------------------------------------------------------------------

export function Jobs() {
  const jobs = useLoad(() => api.jobs(), []);
  return (
    <>
      <h1>Scheduled jobs</h1>
      <p className="lede">
        In production a background worker runs these on schedule. You can run one now; every run is logged either way.
      </p>
      <ErrorNote message={jobs.error} />
      {!jobs.data && !jobs.error && <Loading />}
      <ul className="queue">
        {jobs.data?.map((job) => <JobRow key={job.name} job={job} onRan={() => void jobs.reload()} />)}
      </ul>
    </>
  );
}

function JobRow({ job, onRan }: { job: Job; onRan: () => void }) {
  const action = useAction();
  const last = job.last_run;
  return (
    <li className="panel">
      <h2>{job.description}</h2>
      <dl className="facts">
        <div className="fact">
          <dt>Runs</dt>
          <dd>{job.schedule}</dd>
        </div>
        <div className="fact">
          <dt>Last run</dt>
          <dd>{last ? when(last.finished_at) : "Never"}</dd>
        </div>
      </dl>
      {last && <p className={last.ok ? "confirmed" : "error-note"}>{last.summary}</p>}
      <ErrorNote message={action.error} />
      <button
        type="button"
        className="btn"
        disabled={action.busy}
        onClick={() => void action.run(async () => (await api.runJob(job.name), onRan()))}
      >
        Run now
      </button>
    </li>
  );
}
