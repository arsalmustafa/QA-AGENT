import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AskPage } from "./pages/AskPage";
import { AuthCallbackPage } from "./pages/AuthCallbackPage";
import { IngestPage } from "./pages/IngestPage";
import { LoginPage } from "./pages/LoginPage";
import { ProjectDetailPage } from "./pages/ProjectDetailPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { UploadPage } from "./pages/UploadPage";
import { useAuth } from "./auth/AuthContext";

function LoginOrRedirect() {
  const { isAuthenticated, loading, token } = useAuth();
  if (token && loading) {
    return (
      <div className="page-center">
        <p className="muted">Checking session…</p>
      </div>
    );
  }
  if (isAuthenticated) return <Navigate to="/" replace />;
  return <LoginPage />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginOrRedirect />} />
      <Route path="/auth/callback" element={<AuthCallbackPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route index element={<ProjectsPage />} />
          <Route path="projects/:owner/:repo" element={<ProjectDetailPage />} />
          <Route path="ask" element={<AskPage />} />
          <Route path="ingest" element={<IngestPage />} />
          <Route path="upload" element={<UploadPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
