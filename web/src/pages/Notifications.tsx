import { Link } from "react-router-dom";
import { api } from "../api/client";
import { ErrorNote, Loading, useAction, useLoad } from "../components";
import { when } from "../format";
import { useRefreshUnread } from "../Shell";

export function Notifications() {
  const onRead = useRefreshUnread();
  const inbox = useLoad(() => api.notifications(), []);
  const action = useAction();

  const markRead = () =>
    action.run(async () => {
      inbox.setData(await api.markNotificationsRead());
      onRead();
    });

  return (
    <>
      <h1>Updates</h1>
      <ErrorNote message={inbox.error ?? action.error} />
      {!inbox.data && !inbox.error && <Loading />}
      {inbox.data?.items.length === 0 && (
        <p className="empty">Bids, wins, payments, pickups and settlements will show up here.</p>
      )}
      {inbox.data && inbox.data.unread > 0 && (
        <button type="button" className="btn" disabled={action.busy} onClick={() => void markRead()}>
          Mark all as read
        </button>
      )}
      <ul className="notes">
        {inbox.data?.items.map((n) => (
          <li key={n.id} className={n.read ? undefined : "note-unread"}>
            <p className="note-text">
              {!n.read && <span className="visually-hidden">New: </span>}
              {n.text}
            </p>
            <p className="note-meta">
              {when(n.created_at)}
              {n.emailed && " · emailed"}
              {n.lot_id && (
                <>
                  {" · "}
                  <Link to={`/lots/${n.lot_id}`}>View lot</Link>
                </>
              )}
            </p>
          </li>
        ))}
      </ul>
    </>
  );
}
