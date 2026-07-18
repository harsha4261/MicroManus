import { oauthUrl } from "../api";

export default function Login() {
  return (
    <div className="login-page">
      <div className="login-glow login-glow-left" aria-hidden="true" />
      <div className="login-glow login-glow-right" aria-hidden="true" />
      <div className="center-card login-card">
        <h1>MicroManus</h1>
        <p className="muted">A deep-research agent that thinks, searches, and writes reports.</p>
        <div className="stack">
          <a className="btn btn-primary" href={oauthUrl("google")}>
            Continue with Google
          </a>
          <a className="btn" href={oauthUrl("github")}>
            Continue with GitHub
          </a>
        </div>
      </div>
      <div className="login-profile" aria-label="Profile links">
        <p className="login-profile-name">Harsha Vardhan Reddy Emani</p>
        <div className="login-profile-links">
          <a href="https://github.com/harsha4261" target="_blank" rel="noreferrer">
            GitHub Profile
          </a>
          <a href="https://www.linkedin.com/in/harsha-vardhan-reddy-emani" target="_blank" rel="noreferrer">
            LinkedIn Profile
          </a>
        </div>
      </div>
    </div>
  );
}
