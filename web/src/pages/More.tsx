import { Link } from "react-router-dom";
import { useUser } from "../auth";

type Entry = { to: string; title: string; detail: string };

const IMPACT: Entry = {
  to: "/impact",
  title: "Environmental impact",
  detail: "How much material your trades kept in use, and the emissions that saved.",
};

const ENTRIES: Record<string, Entry[]> = {
  seller: [
    { to: "/requests", title: "Buyer requests", detail: "Materials buyers are asking for right now." },
    { to: "/agreements", title: "Supply agreements", detail: "Regular monthly deals buyers have offered you." },
    IMPACT,
  ],
  buyer: [
    { to: "/requests", title: "Your requests", detail: "Ask sellers for a material you need." },
    {
      to: "/agreements",
      title: "Supply agreements",
      detail: "Offer a regular monthly deal to a seller you have bought from.",
    },
    IMPACT,
  ],
  admin: [
    { to: "/admin/routes", title: "Pickup routes", detail: "The day's pickups in a suggested order for the truck." },
    { to: "/admin/transporters", title: "Transporters", detail: "Logistics partners who collect lots." },
    { to: "/admin/anchors", title: "Record anchors", detail: "Seal the custody record under one fingerprint." },
    { to: "/admin/jobs", title: "Scheduled jobs", detail: "What runs in the background, and when it last ran." },
    { to: "/requests", title: "Buyer requests", detail: "Every request buyers have posted." },
    { to: "/agreements", title: "Supply agreements", detail: "Every agreement offered on the platform." },
    { ...IMPACT, detail: "Material kept in use and emissions saved across the platform." },
  ],
};

export function More() {
  const { role } = useUser();
  return (
    <>
      <h1>More</h1>
      <ul className="menu">
        {(ENTRIES[role] ?? []).map((entry) => (
          <li key={entry.to}>
            <Link to={entry.to}>
              <span className="menu-title">{entry.title}</span>
              <span className="menu-detail">{entry.detail}</span>
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}
