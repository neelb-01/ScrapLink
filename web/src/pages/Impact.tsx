import type { CSSProperties } from "react";
import { api } from "../api/client";
import { useUser } from "../auth";
import { ErrorNote, Loading, useLoad } from "../components";
import { kg } from "../format";
import { metalColour } from "../lots";

const tonnesOrKg = (grams: number) => (grams >= 1_000_000 ? `${(grams / 1_000_000).toFixed(1)} t` : kg(grams));

export function Impact() {
  const user = useUser();
  const impact = useLoad(() => api.impact(), []);
  const whose = { seller: "you sold", buyer: "you bought", admin: "settled on ScrapLink" }[user.role] ?? "";

  if (impact.error) return <ErrorNote message={impact.error} />;
  if (!impact.data) return <Loading />;
  const data = impact.data;
  const heaviest = Math.max(1, ...data.materials.map((m) => m.weight_grams));

  return (
    <>
      <h1>Environmental impact</h1>
      <p className="lede">From the weighbridge weight of every trade {whose} that has been paid out.</p>
      <dl className="figures">
        <div className="figure">
          <dt>Kept in use</dt>
          <dd>{tonnesOrKg(data.weight_grams)}</dd>
        </div>
        <div className="figure">
          <dt>CO₂e avoided, about</dt>
          <dd>{tonnesOrKg(data.co2e_avoided_grams)}</dd>
        </div>
        <div className="figure">
          <dt>Trades</dt>
          <dd>{data.trades}</dd>
        </div>
      </dl>
      {data.materials.length === 0 ? (
        <p className="empty">Nothing yet. Figures appear here once a trade is paid out.</p>
      ) : (
        <section className="panel" aria-labelledby="by-material">
          <h2 id="by-material">By material</h2>
          <ul className="bars">
            {data.materials.map((m) => (
              <li key={m.code} style={{ "--metal": metalColour(m.code) } as CSSProperties}>
                <span className="bar-label">
                  {m.name}
                  <span className="subtle">
                    {" "}
                    {tonnesOrKg(m.weight_grams)}, about {tonnesOrKg(m.co2e_avoided_grams)} CO₂e avoided
                  </span>
                </span>
                <span className="bar" style={{ width: `${(100 * m.weight_grams) / heaviest}%` }} aria-hidden="true" />
              </li>
            ))}
          </ul>
        </section>
      )}
      <p className="aside">
        Emission savings use one rounded factor per material, not a measured life-cycle figure for this supply chain.
        Treat them as an indication, not an audited ESG report.
      </p>
    </>
  );
}
