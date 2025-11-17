import { useEffect, useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { useAuthLogin } from "../api/endpoints";
import type { AuthLoginRequest } from "../api/models/authLoginRequest";
import { useAuthStore } from "../features/auth/store";

const LoginPage = () => {
  const navigate = useNavigate();
  const token = useAuthStore((state) => state.token);
  const initialized = useAuthStore((state) => state.initialized);
  const hydrate = useAuthStore((state) => state.hydrate);
  const loginStore = useAuthStore((state) => state.login);

  const [form, setForm] = useState<AuthLoginRequest>({ username: "", password: "" });
  const [error, setError] = useState<string | null>(null);

  const loginMutation = useAuthLogin({
    mutation: {
      onSuccess: (response) => {
        const payload = response.data;
        loginStore(payload.accessToken, payload.user);
        navigate("/runs", { replace: true });
      },
      onError: (err: any) => {
        const message =
          err?.response?.data?.message || err?.response?.data?.detail || err?.message || "Login failed";
        setError(message);
      },
    },
  });

  useEffect(() => {
    if (!initialized) {
      hydrate();
    }
  }, [initialized, hydrate]);

  if (!initialized && !token) {
    return (
      <div className="auth-view auth-view--splash">
        <div className="auth-panel__card">
          <p>Loading session...</p>
        </div>
      </div>
    );
  }

  if (initialized && token) {
    return <Navigate to="/runs" replace />;
  }

  const handleChange = (evt: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = evt.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (evt: React.FormEvent<HTMLFormElement>) => {
    evt.preventDefault();
    setError(null);
    loginMutation.mutate({ data: form });
  };

  return (
    <div className="auth-view auth-view--solo">
      <section className="auth-panel">
        <div className="auth-panel__card">
          <h2>Welcome back</h2>
          <p className="auth-panel__subtitle">Sign in with your AstraFlow account</p>
          <form className="auth-form" onSubmit={handleSubmit}>
            <label className="stack">
              <span>Username</span>
              <input
                type="text"
                name="username"
                autoComplete="username"
                value={form.username}
                onChange={handleChange}
                placeholder="admin"
                required
              />
            </label>
            <label className="stack">
              <span>Password</span>
              <input
                type="password"
                name="password"
                autoComplete="current-password"
                value={form.password}
                onChange={handleChange}
                placeholder="••••••••"
                required
              />
            </label>
            {error && <p className="error auth-form__error">{error}</p>}
            <button className="btn btn--primary auth-form__submit" type="submit" disabled={loginMutation.isPending}>
              {loginMutation.isPending ? "Signing in..." : "Sign In"}
            </button>
          </form>
          <div className="auth-panel__meta">
            <p>Need an account? Ask your AstraFlow administrator.</p>
            {import.meta.env.VITE_SCHEDULER_TOKEN && <p>Dev token detected — login will persist your JWT.</p>}
          </div>
        </div>
      </section>
    </div>
  );
};

export default LoginPage;
