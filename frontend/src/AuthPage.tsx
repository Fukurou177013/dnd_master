import { useState, type FormEvent } from "react";

import { ApiError } from "./api";
import { useAuth } from "./AuthContext";

type Mode = "login" | "register";

export function AuthPage() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "register") {
        await register(email, password, displayName);
      } else {
        await login(email, password);
      }
    } catch (submitError) {
      setError(
        submitError instanceof ApiError
          ? submitError.message
          : "Не удалось подключиться к серверу",
      );
    } finally {
      setSubmitting(false);
    }
  }

  function switchMode(nextMode: Mode) {
    setMode(nextMode);
    setError(null);
  }

  return (
    <main className="auth-shell">
      <section className="auth-card">
        <div className="brand">
          <span className="brand-mark">D20</span>
          <div>
            <h1>D&amp;D Master</h1>
            <p className="muted">
              Личный мастер по правилам SRD 5.2.1: персонаж, кампания и чат.
            </p>
          </div>
        </div>

        <div className="tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={mode === "login"}
            className={mode === "login" ? "tab active" : "tab"}
            onClick={() => switchMode("login")}
          >
            Вход
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === "register"}
            className={mode === "register" ? "tab active" : "tab"}
            onClick={() => switchMode("register")}
          >
            Регистрация
          </button>
        </div>

        <form className="stack" onSubmit={handleSubmit}>
          {mode === "register" && (
            <label className="field">
              <span>Как вас называть</span>
              <input
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
                minLength={1}
                maxLength={50}
                autoComplete="nickname"
                required
              />
            </label>
          )}

          <label className="field">
            <span>Email</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              maxLength={254}
              required
            />
          </label>

          <label className="field">
            <span>Пароль</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              minLength={mode === "register" ? 12 : 1}
              maxLength={128}
              autoComplete={
                mode === "register" ? "new-password" : "current-password"
              }
              required
            />
            {mode === "register" && (
              <small className="hint">Минимум 12 символов.</small>
            )}
          </label>

          {error && <p className="alert error">{error}</p>}

          <button className="button primary" type="submit" disabled={submitting}>
            {submitting
              ? "Подождите..."
              : mode === "register"
                ? "Создать аккаунт"
                : "Войти"}
          </button>
        </form>

        <ul className="feature-list">
          <li>Сервер проверяет характеристики и броски d20.</li>
          <li>Ответы мастера опираются на проиндексированные правила SRD.</li>
          <li>История и структурированное резюме сохраняются между визитами.</li>
        </ul>
      </section>
    </main>
  );
}
