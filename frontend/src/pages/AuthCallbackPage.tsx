import { useEffect } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function AuthCallbackPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { loginWithToken, isAuthenticated } = useAuth();
  const token = params.get("token");
  const refreshToken = params.get("refresh_token");

  useEffect(() => {
    if (token) {
      loginWithToken(token, refreshToken);
      navigate("/", { replace: true });
    }
  }, [token, refreshToken, loginWithToken, navigate]);

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  if (!token) {
    return (
      <div className="page-center">
        <div className="panel narrow">
          <h1>Login incomplete</h1>
          <p className="muted">No token was returned from GitHub OAuth.</p>
          <a className="btn primary" href="/login">
            Back to login
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="page-center">
      <p className="muted">Signing you in…</p>
    </div>
  );
}
