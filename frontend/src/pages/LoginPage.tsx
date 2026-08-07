import { githubLoginUrl } from "../api/client";

export function LoginPage() {
  return (
    <div className="login-page">
      <div className="login-panel">
        <p className="eyebrow">QA Agent</p>
        <h1>Ask your repos anything.</h1>
        <p className="lede">
          Sign in with GitHub to ingest projects, upload docs, and query code,
          documentation, or security context through the multi-agent API.
        </p>
        <a className="btn primary large" href={githubLoginUrl()}>
          Continue with GitHub
        </a>
        <p className="hint">
          You will be redirected to GitHub, then back here with a session token.
        </p>
      </div>
    </div>
  );
}
