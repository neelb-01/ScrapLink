import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { api } from "./api/client";
import { useAuth, useUser } from "./auth";
import { ThemeToggle } from "./theme";

type NavItem = { to: string; label: string; primary?: boolean };

function navFor(role: string): NavItem[] {
  switch (role) {
    case "buyer":
      return [
        { to: "/", label: "Home" },
        { to: "/market", label: "Market" },
        { to: "/mine", label: "My trades" },
        { to: "/wallet", label: "Wallet" },
        { to: "/more", label: "More" },
      ];
    case "admin":
      return [
        { to: "/admin", label: "Approvals" },
        { to: "/admin/disputes", label: "Disputes" },
        { to: "/admin/prices", label: "Prices" },
        { to: "/mine", label: "All lots" },
        { to: "/more", label: "More" },
      ];
    default:
      return [
        { to: "/", label: "Home" },
        { to: "/lots/new", label: "List a lot", primary: true },
        { to: "/mine", label: "My lots" },
        { to: "/wallet", label: "Wallet" },
        { to: "/more", label: "More" },
      ];
  }
}

const UNREAD_REFRESH_MS = 30_000;
const UnreadContext = createContext<() => void>(() => {});

/** Pages that change what is unread (the updates page) call this to refresh the count. */
export function useRefreshUnread(): () => void {
  return useContext(UnreadContext);
}

export function Shell() {
  const user = useUser();
  const { signOut } = useAuth();
  const { pathname } = useLocation();
  const [unread, setUnread] = useState(0);

  const refreshUnread = useCallback(() => {
    api.notifications().then(
      (inbox) => setUnread(inbox.unread),
      () => {},
    );
  }, []);

  // Recount on every page change, and every half minute while the app is open.
  useEffect(() => {
    refreshUnread();
    const timer = window.setInterval(refreshUnread, UNREAD_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [refreshUnread, pathname]);

  return (
    <UnreadContext.Provider value={refreshUnread}>
      <div className="shell">
        <header className="topbar">
          <span className="brand">ScrapLink</span>
          <span className="who">
            <span className="who-name">{user.business_name ?? user.name}</span>
            <Link to="/notifications" className="updates" aria-label={unread ? `Updates, ${unread} new` : "Updates"}>
              Updates
              {unread > 0 && (
                <span className="badge" aria-hidden="true">
                  {unread > 99 ? "99+" : unread}
                </span>
              )}
            </Link>
            <ThemeToggle />
            <button type="button" className="btn-quiet" onClick={signOut}>
              Sign out
            </button>
          </span>
        </header>
        <main className="page">
          <Outlet />
        </main>
        <nav className="bottombar" aria-label="Main">
          {navFor(user.role).map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end
              className={({ isActive }) =>
                [item.primary ? "nav-primary" : "", isActive ? "nav-active" : ""].join(" ")
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </UnreadContext.Provider>
  );
}
