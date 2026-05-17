import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/store/auth";
import { Map, LayoutDashboard, Plus, FileText, Settings, LogOut } from "lucide-react";
import clsx from "clsx";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/analysis/new", label: "Yeni Analiz", icon: Plus },
  { to: "/reports", label: "Raporlar", icon: FileText },
];

export default function Layout() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="flex h-screen overflow-hidden bg-gray-100">
      {/* Sidebar */}
      <aside className="w-56 flex flex-col bg-primary-900 text-white shadow-xl">
        <div className="flex items-center gap-2 px-5 py-4 border-b border-primary-700">
          <Map size={22} />
          <span className="font-bold text-lg tracking-wide">CAERN</span>
        </div>

        <nav className="flex-1 p-3 space-y-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                  isActive ? "bg-primary-600" : "hover:bg-primary-700"
                )
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
          {user?.role === "admin" && (
            <NavLink
              to="/admin"
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                  isActive ? "bg-primary-600" : "hover:bg-primary-700"
                )
              }
            >
              <Settings size={18} />
              Admin
            </NavLink>
          )}
        </nav>

        <div className="p-3 border-t border-primary-700">
          <div className="text-xs text-primary-300 mb-2 truncate px-1">{user?.email}</div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm hover:bg-primary-700 transition-colors"
          >
            <LogOut size={16} />
            Çıkış
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
