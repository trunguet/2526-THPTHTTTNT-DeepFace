import { useEffect, useState } from "react";
import { getCurrentUser, login } from "./api/auth";
import { listAccessLogs } from "./api/logs";
import AccessPage from "./pages/AccessPage";
import HistoryPage from "./pages/HistoryPage";
import LoginPage from "./pages/LoginPage";
import ProfilePage from "./pages/ProfilePage";
import type { User } from "./types/auth";
import type { AccessLog } from "./types/log";

type UserView = "access" | "history" | "profile";

const TOKEN_STORAGE_KEY = "deepface_user_token";

const navItems: Array<{ id: UserView; label: string }> = [
  { id: "access", label: "Access" },
  { id: "history", label: "History" },
  { id: "profile", label: "Session" },
];

export default function App() {
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem(TOKEN_STORAGE_KEY),
  );
  const [signedInAt, setSignedInAt] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [activeView, setActiveView] = useState<UserView>("access");
  const [logs, setLogs] = useState<AccessLog[]>([]);
  const [isLoadingSession, setIsLoadingSession] = useState(Boolean(token));
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [isLoadingLogs, setIsLoadingLogs] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refreshLogs(currentToken = token) {
    if (!currentToken) {
      return;
    }
    setIsLoadingLogs(true);
    try {
      setLogs(await listAccessLogs(currentToken));
    } finally {
      setIsLoadingLogs(false);
    }
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
        setSignedInAt((current) => current ?? new Date().toISOString());
        await refreshLogs(currentToken);
      } catch (err) {
        localStorage.removeItem(TOKEN_STORAGE_KEY);
        setToken(null);
        setUser(null);
        setSignedInAt(null);
        setError(err instanceof Error ? err.message : "Session expired");
      } finally {
        setIsLoadingSession(false);
      }
    }

    void bootstrapSession();
  }, [token]);

  useEffect(() => {
    if (!token || !user) {
      return;
    }

    const intervalId = window.setInterval(() => {
      void refreshLogs(token);
    }, 3000);

    return () => window.clearInterval(intervalId);
  }, [token, user]);

  async function handleLogin(username: string, password: string) {
    setIsLoggingIn(true);
    setError(null);
    try {
      const response = await login(username, password);
      localStorage.setItem(TOKEN_STORAGE_KEY, response.access_token);
      setToken(response.access_token);
      setUser(response.user);
      setSignedInAt(new Date().toISOString());
      await refreshLogs(response.access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cannot sign in");
    } finally {
      setIsLoggingIn(false);
    }
  }

  function handleLogout() {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken(null);
    setUser(null);
    setSignedInAt(null);
    setLogs([]);
  }

  if (isLoadingSession) {
    return <main className="login-shell">Loading access terminal...</main>;
  }

  if (!token || !user) {
    return (
      <LoginPage error={error} isLoading={isLoggingIn} onLogin={handleLogin} />
    );
  }

  const content =
    activeView === "history" ? (
      <HistoryPage
        isLoading={isLoadingLogs}
        logs={logs.filter((log) => !log.image_path?.startsWith("/app/data/smoke"))}
        onRefresh={() => refreshLogs()}
      />
    ) : activeView === "profile" ? (
      <ProfilePage
        logs={logs.filter((log) => !log.image_path?.startsWith("/app/data/smoke"))}
        signedInAt={signedInAt}
        user={user}
      />
    ) : (
      <AccessPage
        logs={logs.filter((log) => !log.image_path?.startsWith("/app/data/smoke"))}
        token={token}
        onAccessQueued={() => refreshLogs()}
      />
    );

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">DeepFace Access</p>
          <h1>Gate terminal</h1>
        </div>
        <nav className="nav-tabs" aria-label="User navigation">
          {navItems.map((item) => (
            <button
              className={activeView === item.id ? "active" : ""}
              key={item.id}
              onClick={() => setActiveView(item.id)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </nav>
        <div className="topbar-actions">
          <button className="ghost-button" onClick={handleLogout} type="button">
            Sign out
          </button>
        </div>
      </header>
      {content}
    </main>
  );
}
