import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "./AuthContext";

export function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink to="/characters" className="brand compact">
          <span className="brand-mark">D20</span>
          <span>D&amp;D Master</span>
        </NavLink>

        <nav className="main-nav">
          <NavLink
            to="/characters"
            className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
          >
            Персонажи
          </NavLink>
          <NavLink
            to="/campaigns"
            className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
          >
            Кампании
          </NavLink>
        </nav>

        <div className="user-box">
          <span className="muted small">{user?.display_name}</span>
          <button className="button ghost" type="button" onClick={handleLogout}>
            Выйти
          </button>
        </div>
      </header>

      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
