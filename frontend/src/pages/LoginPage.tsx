import { FormEvent, useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../features/auth/AuthContext";

export function LoginPage() {
  const { login, user, loading } = useAuth();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (!loading && user) return <Navigate to="/" replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(username, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка входа");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={onSubmit}>
        <div className="brand-mark">GNO Monitor</div>
        <h1>Вход в систему</h1>
        <p>Мониторинг и предиктивная аналитика глубинно-насосного оборудования</p>
        <div className="form-grid" style={{ marginTop: "1.25rem" }}>
          <label>
            Логин
            <input value={username} onChange={(e) => setUsername(e.target.value)} required />
          </label>
          <label>
            Пароль
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          {error && <div className="state-box error">{error}</div>}
          <button className="btn primary" disabled={busy}>
            {busy ? "Вход..." : "Войти"}
          </button>
        </div>
        <p className="muted" style={{ marginTop: "1rem", fontSize: "0.85rem" }}>
          Учётные данные задаются в `.env` (ADMIN_USERNAME / ADMIN_PASSWORD). Демо-пользователи
          создаются seed-скриптом.
        </p>
      </form>
    </div>
  );
}
