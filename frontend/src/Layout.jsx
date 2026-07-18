import { NavLink, Navigate, Outlet } from "react-router-dom";
import { useAuth } from "./AuthContext";
import { clearToken } from "./api";
import { LANGS, getLang, setLang, t } from "./i18n";

export default function Layout() {
  const { me, loading } = useAuth();

  if (loading) return <div className="center-card">Loading…</div>;
  if (!me) return <Navigate to="/login" replace />;
  if (!me.has_access) return <Navigate to="/paywall" replace />;

  return (
    <div className="app-shell">
      <nav className="topnav">
        <span className="brand">MicroManus</span>
        <NavLink to="/chat" className={({ isActive }) => (isActive ? "active" : "")}>
          {t("chat")}
        </NavLink>
        <NavLink to="/stats" className={({ isActive }) => (isActive ? "active" : "")}>
          {t("stats")}
        </NavLink>
        <NavLink to="/settings" className={({ isActive }) => (isActive ? "active" : "")}>
          {t("settings")}
        </NavLink>
        {me.is_admin && (
          <NavLink to="/admin" className={({ isActive }) => (isActive ? "active" : "")}>
            {t("admin")}
          </NavLink>
        )}
        <span className="spacer" />
        <select className="lang-select" value={getLang()} onChange={(e) => setLang(e.target.value)} aria-label="Language">
          {Object.entries(LANGS).map(([code, label]) => (
            <option key={code} value={code}>
              {label}
            </option>
          ))}
        </select>
        <span className="muted">{me.email}</span>
        <button
          className="btn-link"
          onClick={() => {
            clearToken();
            window.location.href = "/login";
          }}
        >
          {t("logout")}
        </button>
      </nav>
      <Outlet />
    </div>
  );
}
