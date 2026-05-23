import { FormEvent, useState } from "react";

interface LoginPageProps {
  error: string | null;
  isLoading: boolean;
  onLogin: (username: string, password: string) => Promise<void>;
}

export default function LoginPage({ error, isLoading, onLogin }: LoginPageProps) {
  const [username, setUsername] = useState("user");
  const [password, setPassword] = useState("user123");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onLogin(username.trim(), password);
  }

  return (
    <main className="login-shell">
      <form className="login-panel" onSubmit={handleSubmit}>
        <div className="brand-mark">DF</div>
        <p className="eyebrow">Access terminal</p>
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
        <button className="primary-button" disabled={isLoading} type="submit">
          {isLoading ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </main>
  );
}
