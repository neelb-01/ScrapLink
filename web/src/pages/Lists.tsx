import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { useUser } from "../auth";
import { ErrorNote, Loading, LotTag, SelectField, useLoad, usePlaces } from "../components";
import { rupees, when } from "../format";
import { FAMILY_NAMES } from "../lots";

export function MyLots() {
  const user = useUser();
  const { data: lots, error } = useLoad(() => api.lots("mine"), []);
  const title = { buyer: "My trades", admin: "All lots" }[user.role] ?? "My lots";

  return (
    <>
      <h1>{title}</h1>
      <ErrorNote message={error} />
      {!lots && !error && <Loading />}
      {lots?.length === 0 && (
        <div className="empty">
          {user.role === "buyer" ? (
            <p>
              Lots you bid on show up here. <Link to="/market">Find lots in the market</Link>.
            </p>
          ) : user.role === "admin" ? (
            <p>No lots have been created yet.</p>
          ) : (
            <>
              <p>Photograph your first lot to get a price and start taking bids.</p>
              <Link to="/lots/new" className="btn-primary">
                List a lot
              </Link>
            </>
          )}
        </div>
      )}
      <div className="tags">
        {lots?.map((lot) => <LotTag key={lot.id} lot={lot} user={user} />)}
      </div>
    </>
  );
}

export function Market() {
  const user = useUser();
  const places = usePlaces();
  const [family, setFamily] = useState("");
  const [place, setPlace] = useState("");
  const { data: lots, error } = useLoad(() => api.lots("market", { family, place }), [family, place]);
  const filtered = Boolean(family || place);
  return (
    <>
      <h1>Market</h1>
      <p className="lede">
        Lots taking bids now. Most are sealed: nobody sees your bid. Lots marked open bidding show the best
        bid, and you must beat it.
      </p>
      <div className="filters" role="search" aria-label="Filter the market">
        <SelectField label="Material" value={family} onChange={(e) => setFamily(e.target.value)}>
          <option value="">All materials</option>
          {Object.entries(FAMILY_NAMES).map(([code, name]) => (
            <option key={code} value={code}>
              {name}
            </option>
          ))}
        </SelectField>
        <SelectField label="Town" value={place} onChange={(e) => setPlace(e.target.value)}>
          <option value="">Anywhere</option>
          {places.map((p) => (
            <option key={p.code} value={p.code}>
              {p.name}
            </option>
          ))}
        </SelectField>
      </div>
      <ErrorNote message={error} />
      {!lots && !error && <Loading />}
      {lots?.length === 0 && (
        <p className="empty">
          {filtered ? "No lots match. Try another material or town." : "No lots are taking bids right now. Check back later."}
        </p>
      )}
      <div className="tags">
        {lots?.map((lot) => <LotTag key={lot.id} lot={lot} user={user} />)}
      </div>
    </>
  );
}

export function WalletPage() {
  const { data: wallet, error } = useLoad(() => api.wallet(), []);
  const kinds: Record<string, string> = {
    settlement: "Trade settled",
    escrow_funding: "Escrow payment",
    late_payment_returned: "Late payment returned",
    dispute_refund: "Refund after a dispute",
  };
  return (
    <>
      <h1>Wallet</h1>
      <ErrorNote message={error} />
      {!wallet && !error && <Loading />}
      {wallet && (
        <>
          <p className="balance">
            <span className="balance-figure">{rupees(wallet.balance_paise)}</span>
            <span className="balance-label">available</span>
          </p>
          {wallet.entries.length === 0 ? (
            <p className="empty">Money from settled trades and buyer refunds appears here.</p>
          ) : (
            <ul className="ledger">
              {wallet.entries.map((entry, i) => (
                <li key={i}>
                  <span>
                    {kinds[entry.kind] ?? entry.kind}
                    {entry.lot_id && (
                      <>
                        {" "}
                        <Link to={`/lots/${entry.lot_id}`}>View lot</Link>
                      </>
                    )}
                    <span className="ledger-when">{when(entry.created_at)}</span>
                  </span>
                  <span className={entry.amount_paise >= 0 ? "credit" : "debit"}>
                    {entry.amount_paise >= 0 ? "+" : "−"}
                    {rupees(Math.abs(entry.amount_paise))}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <p className="aside">Withdrawals to your bank account are coming in the next release.</p>
        </>
      )}
    </>
  );
}
