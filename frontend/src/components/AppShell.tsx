import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const links = [
  { to: "/", label: "Projects", end: true },
  { to: "/ask", label: "Ask" },
  { to: "/ingest", label: "Ingest" },
  { to: "/upload", label: "Upload" },
];

export function AppShell() {
  const { user, logout } = useAuth();

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden />
          <div>
            <p className="brand-name">QA Agent</p>
            <p className="brand-sub">Code · Docs · Security</p>
          </div>
        </div>

        <nav className="nav">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>

        <div className="user-chip">
          {user?.avatar_url ? (
            <img src={user.avatar_url} alt="" className="avatar" />
          ) : (
            <span className="avatar fallback">{user?.login?.[0]?.toUpperCase()}</span>
          )}
          <span className="user-name">{user?.login}</span>
          <button type="button" className="btn ghost" onClick={logout}>
            Sign out
          </button>
        </div>
      </header>

      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
