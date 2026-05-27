import type { ReactNode, SVGProps } from "react";
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
  isCollapsed: boolean;
  user: User;
  onNavigate: (view: AdminView) => void;
  onLogout: () => void;
  onToggleCollapse: () => void;
}

const baseIconProps: SVGProps<SVGSVGElement> = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
};

const items: Array<{ id: AdminView; label: string; icon: ReactNode }> = [
  {
    id: "dashboard",
    label: "Dashboard",
    icon: (
      <svg {...baseIconProps}>
        <rect x="3" y="3" width="8" height="8" rx="1" />
        <rect x="13" y="3" width="8" height="8" rx="1" />
        <rect x="3" y="13" width="8" height="8" rx="1" />
        <rect x="13" y="13" width="8" height="8" rx="1" />
      </svg>
    ),
  },
  {
    id: "employees",
    label: "Employees",
    icon: (
      <svg {...baseIconProps}>
        <circle cx="12" cy="8" r="3.5" />
        <path d="M4 20c1.6-3 4.3-4.5 8-4.5s6.4 1.5 8 4.5" />
      </svg>
    ),
  },
  {
    id: "cameras",
    label: "Cameras",
    icon: (
      <svg {...baseIconProps}>
        <rect x="3" y="7" width="18" height="12" rx="2" />
        <path d="M8 7l2-3h4l2 3" />
        <circle cx="12" cy="13" r="3" />
      </svg>
    ),
  },
  {
    id: "logs",
    label: "Access logs",
    icon: (
      <svg {...baseIconProps}>
        <circle cx="4" cy="6" r="1" />
        <circle cx="4" cy="12" r="1" />
        <circle cx="4" cy="18" r="1" />
        <path d="M8 6h12M8 12h12M8 18h12" />
      </svg>
    ),
  },
  {
    id: "users",
    label: "Roles",
    icon: (
      <svg {...baseIconProps}>
        <path d="M12 3l7 3v6c0 5-3.5 8-7 9-3.5-1-7-4-7-9V6l7-3z" />
      </svg>
    ),
  },
  {
    id: "settings",
    label: "Settings",
    icon: (
      <svg {...baseIconProps}>
        <circle cx="12" cy="12" r="3" />
        <path d="M12 2v3M12 19v3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M2 12h3M19 12h3M4.9 19.1l2.1-2.1M17 7l2.1-2.1" />
      </svg>
    ),
  },
];

export default function Sidebar({
  activeView,
  isCollapsed,
  user,
  onNavigate,
  onLogout,
  onToggleCollapse,
}: SidebarProps) {
  return (
    <aside className={isCollapsed ? "sidebar collapsed" : "sidebar"}>
      <div className="sidebar-header">
        <div className="brand-mark">DF</div>
        <div className="sidebar-title">
          <p className="eyebrow">Admin console</p>
          <h1>DeepFace Access</h1>
        </div>
        <button
          aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          aria-pressed={isCollapsed}
          className={isCollapsed ? "sidebar-toggle collapsed" : "sidebar-toggle"}
          onClick={onToggleCollapse}
          title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          type="button"
        >
          {isCollapsed ? "DF" : "<"}
        </button>
      </div>

      <nav className="nav-list" aria-label="Admin navigation">
        {items.map((item) => (
          <button
            aria-label={item.label}
            className={activeView === item.id ? "nav-item active" : "nav-item"}
            key={item.id}
            onClick={() => onNavigate(item.id)}
            title={item.label}
            type="button"
          >
            <span className="nav-icon" aria-hidden="true">
              {item.icon}
            </span>
            <span className="nav-label">{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-footer-details">
          <span>{user.username}</span>
          <small>{user.role}</small>
        </div>
        <button className="ghost-button" onClick={onLogout} type="button">
          Sign out
        </button>
      </div>
    </aside>
  );
}
