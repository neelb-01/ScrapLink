import { useState, type CSSProperties, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ErrorNote, Field } from "../components";
import { metalColour } from "../lots";
import { ThemeToggle } from "../theme";
import { HOW_IT_WORKS } from "./Access";

/** Example lots for the hero, at roughly the seeded reference rates. Not live data. */
const EXAMPLE_LOTS = [
  { metal: "copper", name: "Copper", grade: "A", place: "Delhi", weight: "412 kg", line: "Bids open, about ₹680/kg" },
  { metal: "brass", name: "Brass", grade: "B", place: "Jamnagar", weight: "86.5 kg", line: "Best bid ₹37,195" },
  { metal: "aluminium", name: "Aluminium", grade: "A", place: "Pune", weight: "1,240 kg", line: "₹1,95,920 in escrow" },
];

/** Photos from Wikimedia Commons, cropped and resized; their licences require this credit. */
const PHOTO_CREDITS = [
  {
    what: "Scrap shop",
    author: "Mangalapuram123",
    page: "https://commons.wikimedia.org/wiki/File:Scrap_shop_in_INDIA.jpg",
    license: "CC BY-SA 4.0",
    licenseUrl: "https://creativecommons.org/licenses/by-sa/4.0",
  },
  {
    what: "metal strips in Chennai",
    author: "Rakesh.5suthar",
    page: "https://commons.wikimedia.org/wiki/File:Unused_metal_scrap_thrown_away_at_a_public_place_in_a_railway_station_-Chennai_-India_-DSC0001.jpg",
    license: "CC BY-SA 4.0",
    licenseUrl: "https://creativecommons.org/licenses/by-sa/4.0",
  },
  {
    what: "furnace in Guwahati",
    author: "Donvikro",
    page: "https://commons.wikimedia.org/wiki/File:Metallurgical_Furnace_in_Guwahati,_Assam.jpg",
    license: "CC BY-SA 4.0",
    licenseUrl: "https://creativecommons.org/licenses/by-sa/4.0",
  },
  {
    what: "weighbridge in Hooghly",
    author: "Biswarup Ganguly",
    page: "https://commons.wikimedia.org/wiki/File:Karma_Computer_Weighbridge_-_Chakundi_-_NH_6_-_Hooghly_-_2017-07-06_0519.JPG",
    license: "CC BY 3.0",
    licenseUrl: "https://creativecommons.org/licenses/by/3.0",
  },
];

const AUDIENCES = [
  {
    id: "sellers",
    as: "seller",
    title: "For sellers",
    who: "Scrap dealers, workshops and factories with metal to move.",
    photo: "/landing/strip-scrap.webp",
    alt: "Strips of discarded sheet metal piled at a railway station in Chennai",
    points: [
      "Take a photo. ScrapLink suggests the material, and you confirm it.",
      "See a price range from today's rates before you list.",
      "The highest bid wins. You are paid for the weight on the weighbridge.",
    ],
  },
  {
    id: "buyers",
    as: "buyer",
    title: "For buyers",
    who: "Recyclers and smelters buying in volume. A GSTIN is needed.",
    photo: "/landing/furnace.webp",
    alt: "Molten metal poured from a ladle at a furnace in Guwahati, Assam",
    points: [
      "Every seller's business details are checked before they can list.",
      "Bid on lots near you, or post a request for what you need.",
      "Get a numbered invoice and a certificate for every trade.",
    ],
  },
] as const;

/** What protects each side, in the order a trade meets it. */
const SAFEGUARDS = [
  {
    title: "Checked accounts",
    detail: "An admin approves every seller and buyer before their first trade.",
  },
  {
    title: "Escrow first",
    figure: "24 h",
    detail: "The buyer pays within 24 hours of winning. Nothing is picked up until the money is held.",
  },
  {
    title: "Weighed at pickup",
    detail: "The weighbridge reading and slip photo are kept as recorded, never overwritten.",
    photo: "/landing/weighbridge.webp",
    alt: "Trucks at a computerised weighbridge beside a highway in Hooghly, West Bengal",
  },
  {
    title: "Disputes go to a person",
    detail: "If the weight is contested, an admin settles it and the record shows how.",
  },
];

const CERTIFICATE_ID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;

/** Takes the number printed on a certificate, or the whole check link, and opens the public check. */
function CertificateCheck() {
  const navigate = useNavigate();
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const id = value.match(CERTIFICATE_ID)?.[0];
    if (!id) {
      setError("That doesn't look like a certificate number. It has 36 characters, in five groups.");
      return;
    }
    navigate(`/certificates/${id.toLowerCase()}/verify`);
  };

  return (
    <form className="check-form" onSubmit={submit} noValidate>
      <Field
        label="Certificate number"
        autoComplete="off"
        spellCheck={false}
        hint='Printed under the certificate title. You can paste its "Verify at" link instead.'
        value={value}
        onChange={(e) => {
          setValue(e.target.value);
          setError(null);
        }}
      />
      <ErrorNote message={error} />
      <button className="btn">Check it</button>
    </form>
  );
}

/** The public front page: what ScrapLink is, and the ways in. Signed-in people never see it. */
export function Landing() {
  return (
    <div className="landing">
      <header className="landing-bar">
        <Link to="/" className="wordmark" aria-label="ScrapLink home">
          ScrapLink
        </Link>
        <nav className="landing-nav" aria-label="Sections">
          <a href="#how">How it works</a>
          <a href="#sellers">Sellers</a>
          <a href="#buyers">Buyers</a>
          <a href="#check">Check a certificate</a>
        </nav>
        <div className="landing-ways">
          <ThemeToggle />
          <Link to="/signin" className="landing-signin">
            Sign in
          </Link>
          <Link to="/register" className="btn-primary landing-join">
            Create an account
          </Link>
        </div>
      </header>

      <main>
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-copy">
            <h1 id="hero-title">Sell scrap at a fair price. Get paid safely.</h1>
            <p className="hero-sub">
              Approved recyclers bid on your lot, and their money waits in escrow until the weight
              is confirmed.
            </p>
            <div className="row hero-actions">
              <Link to="/register" className="btn-primary">
                Create an account
              </Link>
              <Link to="/signin" className="btn">
                Sign in
              </Link>
            </div>
          </div>
          <figure className="hero-lots">
            <img
              className="hero-photo"
              src="/landing/scrap-shop-1200.webp"
              srcSet="/landing/scrap-shop-640.webp 640w, /landing/scrap-shop-1200.webp 1200w"
              sizes="(min-width: 900px) 46vw, 100vw"
              width={1200}
              height={900}
              fetchPriority="high"
              alt="Used cast-iron pulleys, gears and fittings stacked on shelves in an Indian scrap shop"
            />
            <ul className="hero-tags">
              {EXAMPLE_LOTS.map((lot) => (
                <li
                  key={lot.metal}
                  className="tag"
                  style={{ "--metal": metalColour(lot.metal) } as CSSProperties}
                >
                  <span className="tag-hole" aria-hidden="true" />
                  <span className="tag-body">
                    <span className="tag-metal">
                      {lot.name}
                      <span className="tag-grade">Grade {lot.grade}</span>
                    </span>
                    <span className="tag-place">{lot.place}</span>
                    <span className="tag-figures">
                      <span className="tag-weight">{lot.weight}</span>
                      <span className="tag-price">{lot.line}</span>
                    </span>
                  </span>
                </li>
              ))}
            </ul>
            <figcaption>Example lots, as sellers and buyers see them.</figcaption>
          </figure>
        </section>

        <section id="how" className="landing-how" aria-labelledby="how-title">
          <h2 id="how-title">How a trade works</h2>
          <ol className="rail">
            {HOW_IT_WORKS.map((step) => (
              <li key={step.title} style={{ "--metal": step.metal } as CSSProperties}>
                <span className="how-plate" aria-hidden="true" />
                <span className="how-title">{step.title}</span>
                <span className="how-detail">{step.detail}</span>
              </li>
            ))}
          </ol>
        </section>

        <section className="audiences" aria-label="Who ScrapLink is for">
          {AUDIENCES.map((a) => (
            <article key={a.id} id={a.id} className={`audience audience-${a.as}`}>
              <img
                className="audience-photo"
                src={a.photo}
                alt={a.alt}
                width={960}
                height={540}
                loading="lazy"
                decoding="async"
              />
              <h2>{a.title}</h2>
              <p className="audience-who">{a.who}</p>
              <ul className="audience-points">
                {a.points.map((point) => (
                  <li key={point}>{point}</li>
                ))}
              </ul>
              <Link to={`/register?as=${a.as}`} className={a.as === "seller" ? "btn-primary" : "btn"}>
                Create an account
              </Link>
            </article>
          ))}
        </section>

        <section className="safeguards" aria-labelledby="safe-title">
          <h2 id="safe-title">What keeps both sides safe</h2>
          <ul className="safe-grid">
            {SAFEGUARDS.map((s) => (
              <li key={s.title}>
                {s.photo && (
                  <img
                    className="safe-photo"
                    src={s.photo}
                    alt={s.alt}
                    width={960}
                    height={640}
                    loading="lazy"
                    decoding="async"
                  />
                )}
                {s.figure && <span className="safe-figure">{s.figure}</span>}
                <span>
                  <span className="safe-title">{s.title}</span>
                  <span className="safe-detail">{s.detail}</span>
                </span>
              </li>
            ))}
          </ul>
        </section>

        <section id="check" className="cert-check" aria-labelledby="check-title">
          <div className="check-copy">
            <h2 id="check-title">Holding a ScrapLink certificate?</h2>
            <p>
              Each trade's steps are recorded in order, and the certificate carries a seal of that
              record. Anyone can check it here, with no account.
            </p>
          </div>
          <CertificateCheck />
        </section>
      </main>

      <footer className="landing-foot">
        <span className="wordmark">ScrapLink</span>
        <p>Scrap trade across India, with escrow, weighbridge checks and certificates.</p>
        <nav className="row" aria-label="Account">
          <Link to="/signin">Sign in</Link>
          <Link to="/register">Create an account</Link>
        </nav>
        <p className="landing-credits">
          Photos from Wikimedia Commons, cropped and resized:{" "}
          {PHOTO_CREDITS.map((c, i) => (
            <span key={c.page}>
              <a href={c.page}>{c.what}</a> by {c.author} (<a href={c.licenseUrl}>{c.license}</a>)
              {i < PHOTO_CREDITS.length - 1 ? "; " : "."}
            </span>
          ))}
        </p>
      </footer>
    </div>
  );
}
