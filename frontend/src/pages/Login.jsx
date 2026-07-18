import { oauthUrl } from "../api";

export default function Login() {
  return (
    <div className="center-card">
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
  );
}
