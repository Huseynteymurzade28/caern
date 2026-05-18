import { Outlet, NavLink, useNavigate, useLocation } from "react-router-dom";
import { useAuthStore } from "@/store/auth";
import { Globe2, LayoutDashboard, Plus, FileText, Shield, LogOut } from "lucide-react";
import clsx from "clsx";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/analysis/new", label: "Yeni Analiz", icon: Plus },
  { to: "/reports", label: "Raporlar", icon: FileText },
];

export default function Layout() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();

  // MapScreen ekraninda navbar-only layout (sidebar yok — MapScreen kendi
  // sol/sag panellerini yonetiyor).
  const isMap = location.pathname.startsWith("/map/");

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* NAVBAR */}
      <header className="flex-shrink-0 h-14 bg-bg-panel/95 backdrop-blur border-b border-border flex items-center px-5 gap-6 z-30">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded bg-gradient-to-br from-accent/30 to-accent/10 flex items-center justify-center border border-accent/40">
            <Globe2 size={18} className="text-accent" />
          </div>
          <div>
            <div className="text-base font-bold tracking-wide text-text-primary leading-none">CAERN</div>
            <div className="text-[9px] uppercase tracking-[0.18em] text-text-muted mt-0.5">Geo Change Detection</div>
          </div>
        </div>

        <nav className="flex items-center gap-1 ml-4">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-1.5 px-3 h-9 rounded text-sm font-medium transition-colors",
                  isActive
                    ? "text-accent bg-accent/10 border border-accent/30"
                    : "text-text-muted hover:text-text-primary hover:bg-bg-elev"
                )
              }
            >
              <Icon size={14} />
              {label}
            </NavLink>
          ))}
          {user?.role === "admin" && (
            <NavLink
              to="/admin"
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-1.5 px-3 h-9 rounded text-sm font-medium transition-colors",
                  isActive
                    ? "text-accent bg-accent/10 border border-accent/30"
                    : "text-text-muted hover:text-text-primary hover:bg-bg-elev"
                )
              }
            >
              <Shield size={14} />
              Admin
            </NavLink>
          )}
        </nav>

        <div className="flex-1" />

        <div className="flex items-center gap-3 text-xs">
          <div className="text-right leading-tight">
            <div className="text-text-primary font-medium">{user?.username || user?.email}</div>
            <div className="text-text-subtle uppercase tracking-wide text-[9px]">
              {user?.role}
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 px-2.5 h-8 rounded border border-border text-text-muted hover:text-accent-red hover:border-accent-red/50 transition-colors"
            title="Çıkış"
          >
            <LogOut size={14} />
          </button>
        </div>
      </header>

      <main className={clsx("flex-1 overflow-hidden", isMap ? "" : "overflow-auto")}>
        <Outlet />
      </main>
    </div>
  );
}
