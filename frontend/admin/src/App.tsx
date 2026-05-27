import { FormEvent, useEffect, useState } from "react";
import { listAccessLogs } from "./api/access";
import { getCurrentUser, login } from "./api/auth";
import { listCameras } from "./api/cameras";
import { listEmployees } from "./api/employees";
import Sidebar, { type AdminView } from "./components/Sidebar";
import AccessLogPage from "./pages/AccessLogPage";
import AdminDashboard from "./pages/AdminDashboard";
import CameraPage from "./pages/CameraPage";
import EmployeePage from "./pages/EmployeePage";
import SettingsPage from "./pages/SettingsPage";
import UserPage from "./pages/UserPage";
import type { Camera } from "./types/camera";
import type { Employee } from "./types/employee";
import type { AccessLog } from "./types/log";
import type { User } from "./types/user";

const TOKEN_STORAGE_KEY = "deepface_admin_token";
const SIDEBAR_STORAGE_KEY = "deepface_admin_sidebar";
const THEME_STORAGE_KEY = "deepface_admin_theme";

type ThemeMode = "light" | "dark";

export default function App() {
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem(TOKEN_STORAGE_KEY),
  );
  const [user, setUser] = useState<User | null>(null);
  const [activeView, setActiveView] = useState<AdminView>("dashboard");
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(
    () => localStorage.getItem(SIDEBAR_STORAGE_KEY) === "collapsed",
  );
  const [theme, setTheme] = useState<ThemeMode>(() => {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "light" || stored === "dark") {
      return stored;
    }
    if (
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-color-scheme: dark)").matches
    ) {
      return "dark";
    }
    return "light";
  });
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [logs, setLogs] = useState<AccessLog[]>([]);
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin123");
  const [isLoadingSession, setIsLoadingSession] = useState(Boolean(token));
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refreshOverview(currentToken = token) {
    if (!currentToken) {
      return;
    }
    const [employeeData, cameraData, logData] = await Promise.all([
      listEmployees(currentToken),
      listCameras(currentToken),
      listAccessLogs(currentToken),
    ]);
    setEmployees(employeeData);
    setCameras(cameraData);
    setLogs(logData);
  }

  useEffect(() => {
    if (!token) {
      setIsLoadingSession(false);
      return;
    }

    const currentToken = token;

    async function bootstrapSession() {
      setError(null);
      try {
        const currentUser = await getCurrentUser(currentToken);
        setUser(currentUser);
        await refreshOverview(currentToken);
      } catch (err) {
        localStorage.removeItem(TOKEN_STORAGE_KEY);
        setToken(null);
        setUser(null);
        setError(err instanceof Error ? err.message : "Session expired");
      } finally {
        setIsLoadingSession(false);
      }
    }

    void bootstrapSession();
  }, [token]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoggingIn(true);
    setError(null);
    try {
      const response = await login(username.trim(), password);
      localStorage.setItem(TOKEN_STORAGE_KEY, response.access_token);
      setToken(response.access_token);
      setUser(response.user);
      await refreshOverview(response.access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cannot sign in");
    } finally {
      setIsLoggingIn(false);
    }
  }

  function handleLogout() {
    if (!window.confirm("Are you sure you want to sign out?")) {
      return;
    }

    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken(null);
    setUser(null);
    setEmployees([]);
    setCameras([]);
    setLogs([]);
  }

  function handleToggleSidebar() {
    setIsSidebarCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(
        SIDEBAR_STORAGE_KEY,
        next ? "collapsed" : "expanded",
      );
      return next;
    });
  }

  function handleToggleTheme() {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  }

  const activeEmployees = employees.filter(
    (employee) => employee.status === "active",
  );
  const activeCameras = cameras.filter((camera) => camera.status === "active");

  if (isLoadingSession) {
    return <main className="login-shell">Loading admin session...</main>;
  }

  if (!token || !user) {
    return (
      <main className="login-shell">
        <form className="login-panel" onSubmit={handleLogin}>
          <div className="brand-mark">DF</div>
          <p className="eyebrow">Admin console</p>
          <h1>DeepFace Access</h1>
          {error ? <div className="alert error">{error}</div> : null}
          <label>
            Username
            <input
              required
              value={username}
              onChange={(event) => setUsername(event.target.value)}
            />
          </label>
          <label>
            Password
            <input
              required
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          <button className="primary-button" disabled={isLoggingIn} type="submit">
            {isLoggingIn ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </main>
    );
  }

  const content =
    activeView === "employees" ? (
      <EmployeePage token={token} onEmployeesChange={setEmployees} />
    ) : activeView === "cameras" ? (
      <CameraPage token={token} onCamerasChange={setCameras} />
    ) : activeView === "logs" ? (
      <AccessLogPage token={token} onLogsChange={setLogs} />
    ) : activeView === "users" ? (
      <UserPage currentUser={user} token={token} />
    ) : activeView === "settings" ? (
      <SettingsPage
        camerasCount={activeCameras.length}
        employeesCount={activeEmployees.length}
        logsCount={logs.length}
        token={token}
        user={user}
      />
    ) : (
      <AdminDashboard
        cameras={activeCameras}
        employees={activeEmployees}
        logs={logs}
        onRefresh={() => void refreshOverview()}
      />
    );

  return (
    <main className={isSidebarCollapsed ? "app-shell sidebar-collapsed" : "app-shell"}>
      <Sidebar
        activeView={activeView}
        isCollapsed={isSidebarCollapsed}
        onLogout={handleLogout}
        onNavigate={setActiveView}
        onToggleCollapse={handleToggleSidebar}
        onToggleTheme={handleToggleTheme}
        theme={theme}
        user={user}
      />
      <section className="content-shell">{content}</section>
    </main>
  );
}
