import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { apiFetch } from "../api";
import { useAuth } from "../AuthContext";

export default function Paywall() {
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { refresh } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();

  useEffect(() => {
    if (params.get("checkout") === "success") {
      // Stripe webhook may land a beat after the redirect; poll briefly.
      let attempts = 0;
      const interval = setInterval(async () => {
        attempts += 1;
        const me = await refresh();
        if (me?.has_access || attempts > 8) {
          clearInterval(interval);
          if (me?.has_access) navigate("/chat", { replace: true });
        }
      }, 1500);
      return () => clearInterval(interval);
    }
  }, []);

  const redeemCoupon = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await apiFetch("/billing/coupon", { method: "POST", body: JSON.stringify({ code }) });
      await refresh();
      navigate("/chat", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const startCheckout = async () => {
    setBusy(true);
    try {
      const { url } = await apiFetch("/billing/checkout", { method: "POST" });
      window.location.href = url;
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <div className="center-card">
      <h1>Unlock MicroManus</h1>
      <p className="muted">Get 5 credits (1 credit = 1 research chat message) to get started.</p>

      <form onSubmit={redeemCoupon} className="stack">
        <input placeholder="Coupon code" value={code} onChange={(e) => setCode(e.target.value)} />
        <button className="btn btn-primary" disabled={busy || !code}>
          Redeem coupon
        </button>
      </form>

      <div className="divider">or</div>

      <button className="btn" onClick={startCheckout} disabled={busy}>
        Add card & pay $5
      </button>

      {error && <p className="error">{error}</p>}
    </div>
  );
}
