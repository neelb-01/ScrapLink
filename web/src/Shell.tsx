import { NavLink, Outlet } from "react-router-dom";
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

export function Shell() {
  const user = useUser();
  const { signOut } = useAuth();
  return (
    <div className="shell">
      <header className="topbar">
        <span className="brand">ScrapLink</span>
        <span className="who">
          {user.business_name ?? user.name}
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
  );
}
