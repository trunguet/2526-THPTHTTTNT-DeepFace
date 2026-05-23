import type { User } from "../types/user";

export type AdminView =
  | "dashboard"
  | "employees"
  | "cameras"
  | "logs"
  | "users"
  | "settings";

interface SidebarProps {
  activeView: AdminView;
  user: User;
  onNavigate: (view: AdminView) => void;
  onLogout: () => void;
}

const items: Array<{ id: AdminView; label: string }> = [
  { id: "dashboard", label: "Dashboard" },
  { id: "employees", label: "Employees" },
  { id: "cameras", label: "Cameras" },
  { id: "logs", label: "Access logs" },
  { id: "users", label: "Roles" },
  { id: "settings", label: "Settings" },
];

export default function Sidebar({
  activeView,
  user,
  onNavigate,
  onLogout,
}: SidebarProps) {
  return (
    <aside className="sidebar">
      <div>
        <div className="brand-mark">DF</div>
        <p className="eyebrow">Admin console</p>
        <h1>DeepFace Access</h1>
      </div>

      <nav className="nav-list" aria-label="Admin navigation">
        {items.map((item) => (
          <button
            className={activeView === item.id ? "nav-item active" : "nav-item"}
            key={item.id}
            onClick={() => onNavigate(item.id)}
            type="button"
          >
            {item.label}
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <span>{user.username}</span>
        <small>{user.role}</small>
        <button className="ghost-button" onClick={onLogout} type="button">
          Sign out
        </button>
      </div>
    </aside>
  );
}
