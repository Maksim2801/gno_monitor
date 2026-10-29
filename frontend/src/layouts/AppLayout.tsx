import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../features/auth/AuthContext";
import { alertsApi } from "../api/endpoints";

const links = [
  { to: "/", label: "Панель мониторинга" },
  { to: "/wells", label: "Скважины" },
  { to: "/telemetry", label: "Телеметрия" },
  { to: "/analytics", label: "Аналитика" },
  { to: "/events", label: "События" },
  { to: "/alerts", label: "Уведомления" },
  { to: "/reports", label: "Отчёты" },
];

export function AppLayout() {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();
  const { data: alerts } = useQuery({
    queryKey: ["alerts-badge"],
    queryFn: () => alertsApi.list({ page: 1, page_size: 1, status: "new" }),
    refetchInterval: 30000,
  });

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">Нефтяной фонд</div>
          <div className="brand-title">GNO Monitor</div>
        </div>
        <nav className="nav-list">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.to === "/"}
              className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
            >
              {l.label}
            </NavLink>
          ))}
          {isAdmin && (
            <NavLink
              to="/admin"
              className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
            >
              Администрирование
            </NavLink>
          )}
        </nav>
      </aside>
      <div className="main-area">
        <header className="topbar">
          <div className="muted">Мониторинг и предиктивная аналитика ГНО</div>
          <div className="topbar-right">
            <button className="btn ghost" onClick={() => navigate("/alerts")}>
              Тревоги: {alerts?.total ?? 0}
            </button>
            <div>
              <div>{user?.full_name}</div>
              <div className="muted" style={{ fontSize: "0.8rem" }}>
                {user?.role_name}
              </div>
            </div>
            <button className="btn" onClick={logout}>
              Выход
            </button>
          </div>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
