import type { CSSProperties, ReactNode } from "react";
import { Link } from "react-router-dom";
import { api, type Lot, type User, type Wallet } from "../api/client";
import { useUser } from "../auth";
import { ErrorNote, useLoad } from "../components";
import { kg, perKg, rupees, timeLeft, when } from "../format";
import { isWinner, metalColour } from "../lots";

// Each role's home: what needs them now first, then where things stand. Built only from the
// lots and wallet endpoints the rest of the app already uses.

type Task = { lot: Lot; detail: string; action: string; to: string };
type Figure = { label: string; value: string; to?: string };

/** Sold but not yet paid out: the seller and buyer are both still involved. */
const IN_PROGRESS = new Set(["awarded", "funded", "pickup_scheduled", "delivered", "disputed"]);

const sum = (values: number[]) => values.reduce((total, v) => total + v, 0);
const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;

function sellerTasks(lots: Lot[]): Task[] {
  return lots.flatMap((lot): Task[] => {
    const to = `/lots/${lot.id}`;
    if (lot.status === "draft")
      return lot.estimate
        ? [{ lot, detail: "Priced. Choose how long to take bids.", action: "Finish listing", to: `${to}/sell` }]
        : [
            {
              lot,
              detail: `Photographed ${when(lot.created_at)}. Choose the metal, condition and weight.`,
              action: "Finish listing",
              to: `${to}/details`,
            },
          ];
    if (lot.status === "delivered" && lot.measured_weight_grams != null)
      return [
        {
          lot,
          detail: `Weighed at ${kg(lot.measured_weight_grams)}. Check the reading against the slip.`,
          action: "Check the weight",
          to,
        },
      ];
    return [];
  });
}

function buyerTasks(lots: Lot[], user: User): Task[] {
  return lots.flatMap((lot): Task[] => {
    if (!isWinner(lot, user) || !lot.award) return [];
    const to = `/lots/${lot.id}`;
    switch (lot.status) {
      case "awarded":
        return [
          {
            lot,
            detail: `You won at ${perKg(lot.award.rate_paise_per_kg)}. Pay ${rupees(lot.award.escrow_required_paise)} to confirm.`,
            action: "Pay now",
            to,
          },
        ];
      case "funded":
        return [{ lot, detail: "Paid into escrow. Choose a pickup time.", action: "Book pickup", to }];
      case "pickup_scheduled":
        return [
          {
            lot,
            detail: `Pickup ${lot.pickup_at ? when(lot.pickup_at) : "booked"}. Enter the weighbridge reading after weighing.`,
            action: "Enter weight",
            to,
          },
        ];
      default:
        return [];
    }
  });
}

function lotName(lot: Lot): string {
  return lot.material_name ?? "Metal not chosen yet";
}

function lotWeight(lot: Lot): string | null {
  const grams = lot.measured_weight_grams ?? lot.declared_weight_grams;
  return grams ? kg(grams) : null;
}

function metal(lot: Lot): CSSProperties {
  return { "--metal": metalColour(lot.material_code) } as CSSProperties;
}

// --- Building blocks ----------------------------------------------------------------------

function Greeting({ user }: { user: User }) {
  return (
    <div className="dash-head">
      <h1>Hello, {user.name}</h1>
      {user.business_name && <p className="lede">{user.business_name}</p>}
    </div>
  );
}

function Tasks({ tasks }: { tasks: Task[] }) {
  return (
    <section className="dash-tasks" aria-labelledby="tasks-title">
      <h2 id="tasks-title">Needs you</h2>
      {tasks.length === 0 ? (
        <p className="all-clear">Nothing needs you right now.</p>
      ) : (
        <ul className="tasks">
          {tasks.map((task) => (
            <li key={task.lot.id} className="task" style={metal(task.lot)}>
              <span className="task-text">
                <span className="task-what">
                  {task.lot.material_name ?? "New lot"}
                  {lotWeight(task.lot) && <span className="task-weight">{lotWeight(task.lot)}</span>}
                </span>
                <span className="task-detail">{task.detail}</span>
              </span>
              <Link to={task.to} className="btn-primary task-action">
                {task.action}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function Figures({ items }: { items: Figure[] }) {
  return (
    <section className="dash-figures" aria-label="Your numbers">
      <dl className="figures">
        {items.map((figure) => (
          <div key={figure.label} className="figure">
            <dt>{figure.label}</dt>
            <dd>{figure.to ? <Link to={figure.to}>{figure.value}</Link> : figure.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function LotRows({
  title,
  lots,
  side,
  empty,
  more,
}: {
  title: string;
  lots: Lot[];
  side: (lot: Lot) => ReactNode;
  empty: string;
  more?: { to: string; label: string };
}) {
  const id = `rows-${title.replace(/\W+/g, "-").toLowerCase()}`;
  return (
    <section className="dash-rows" aria-labelledby={id}>
      <h2 id={id}>{title}</h2>
      {lots.length === 0 ? (
        <p className="subtle">{empty}</p>
      ) : (
        <ul className="lot-rows">
          {lots.map((lot) => (
            <li key={lot.id}>
              <Link to={`/lots/${lot.id}`} className="lot-row" style={metal(lot)}>
                <span className="lot-row-plate" aria-hidden="true" />
                <span className="lot-row-main">
                  <span className="lot-row-name">
                    {lotName(lot)}
                    {lot.grade && <span className="lot-row-grade">Grade {lot.grade}</span>}
                  </span>
                  {lotWeight(lot) && <span className="lot-row-weight">{lotWeight(lot)}</span>}
                </span>
                <span className="lot-row-side">{side(lot)}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
      {more && (
        <Link to={more.to} className="dash-more">
          {more.label}
        </Link>
      )}
    </section>
  );
}

function closing(lot: Lot): ReactNode {
  return lot.auction_closes_at ? <span className="lot-row-time">{timeLeft(lot.auction_closes_at)}</span> : null;
}

/** Holds the dashboard's shape while it loads, so nothing jumps when the data lands. */
function Placeholder() {
  return (
    <div className="dash" aria-busy="true">
      <span className="visually-hidden">Loading</span>
      <div className="dash-tasks">
        <div className="skeleton skeleton-heading" />
        <div className="skeleton skeleton-task" />
        <div className="skeleton skeleton-task" />
      </div>
      <div className="dash-figures">
        <div className="skeleton skeleton-figures" />
      </div>
    </div>
  );
}

function Failed({ message, retry }: { message: string; retry: () => void }) {
  return (
    <div className="stack">
      <ErrorNote message={message} />
      <button type="button" className="btn" onClick={retry}>
        Try again
      </button>
    </div>
  );
}

// --- Seller -------------------------------------------------------------------------------

export function SellerDashboard() {
  const user = useUser();
  const { data, error, reload } = useLoad(() => Promise.all([api.lots("mine"), api.wallet()]), []);
  return (
    <>
      <Greeting user={user} />
      {error ? (
        <Failed message={error} retry={() => void reload()} />
      ) : !data ? (
        <Placeholder />
      ) : (
        <SellerBody lots={data[0]} wallet={data[1]} />
      )}
    </>
  );
}

function SellerBody({ lots, wallet }: { lots: Lot[]; wallet: Wallet }) {
  if (lots.length === 0) {
    return (
      <div className="first-run">
        <h2>List your first lot</h2>
        <p>Photograph a lot to see a fair price range, then let recyclers bid on it.</p>
        <Link to="/lots/new" className="btn-primary">
          List a lot
        </Link>
      </div>
    );
  }

  const live = lots.filter((l) => l.status === "listed");
  const inProgress = lots.filter((l) => IN_PROGRESS.has(l.status));
  const paidOut = sum(lots.filter((l) => l.status === "settled").map((l) => l.settled_amount_paise ?? 0));

  return (
    <div className="dash">
      <Tasks tasks={sellerTasks(lots)} />
      <Figures
        items={[
          { label: "In your wallet", value: rupees(wallet.balance_paise), to: "/wallet" },
          { label: "Taking bids", value: String(live.length) },
          { label: "Sold, in progress", value: String(inProgress.length) },
          { label: "Paid out so far", value: rupees(paidOut) },
        ]}
      />
      <LotRows
        title="Taking bids now"
        lots={live}
        empty="None of your lots are taking bids."
        side={(lot) => (
          <>
            <span className="lot-row-figure">{lot.bid_count ? plural(lot.bid_count, "bid") : "No bids yet"}</span>
            {closing(lot)}
          </>
        )}
        more={{ to: "/mine", label: "See all your lots" }}
      />
    </div>
  );
}

// --- Buyer --------------------------------------------------------------------------------

export function BuyerDashboard() {
  const user = useUser();
  const { data, error, reload } = useLoad(
    () => Promise.all([api.lots("mine"), api.lots("market"), api.wallet()]),
    [],
  );
  return (
    <>
      <Greeting user={user} />
      {error ? (
        <Failed message={error} retry={() => void reload()} />
      ) : !data ? (
        <Placeholder />
      ) : (
        <BuyerBody user={user} mine={data[0]} market={data[1]} wallet={data[2]} />
      )}
    </>
  );
}

function BuyerBody({ user, mine, market, wallet }: { user: User; mine: Lot[]; market: Lot[]; wallet: Wallet }) {
  const openBids = mine.filter((l) => l.status === "listed" && l.my_bid_rate_paise_per_kg != null);
  const won = mine.filter((l) => isWinner(l, user) && IN_PROGRESS.has(l.status));
  const bought = sum(
    mine.filter((l) => isWinner(l, user) && l.status === "settled").map((l) => l.settled_amount_paise ?? 0),
  );
  // The market is already ordered by closing time; lots this buyer bid on are listed above.
  const closingSoon = market.filter((l) => l.my_bid_rate_paise_per_kg == null).slice(0, 3);

  return (
    <div className="dash">
      <Tasks tasks={buyerTasks(mine, user)} />
      <Figures
        items={[
          { label: "In your wallet", value: rupees(wallet.balance_paise), to: "/wallet" },
          { label: "Open bids", value: String(openBids.length) },
          { label: "Won, in progress", value: String(won.length) },
          { label: "Bought so far", value: rupees(bought) },
        ]}
      />
      <LotRows
        title="Your bids"
        lots={openBids}
        empty="You have no open bids."
        side={(lot) => (
          <>
            <span className="lot-row-figure">You bid {perKg(lot.my_bid_rate_paise_per_kg!)}</span>
            {closing(lot)}
          </>
        )}
      />
      <LotRows
        title="Closing soon"
        lots={closingSoon}
        empty="No new lots are taking bids right now."
        side={(lot) => (
          <>
            {lot.estimate && <span className="lot-row-figure">Fair price {perKg(lot.estimate.rate_paise_per_kg)}</span>}
            {closing(lot)}
          </>
        )}
        more={{ to: "/market", label: "Open the market" }}
      />
    </div>
  );
}
