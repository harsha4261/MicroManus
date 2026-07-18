import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { consumeAuthHash } from "../api";
import { useAuth } from "../AuthContext";

export default function AuthCallback() {
  const navigate = useNavigate();
  const { refresh } = useAuth();

  useEffect(() => {
    if (!consumeAuthHash()) {
      navigate("/login", { replace: true });
      return;
    }
    refresh().then(() => navigate("/", { replace: true }));
  }, []);

  return <div className="center-card">Signing you in…</div>;
}
