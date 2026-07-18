import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { setRefreshToken, setToken } from "../api";
import { useAuth } from "../AuthContext";

export default function AuthCallback() {
  const navigate = useNavigate();
  const { refresh } = useAuth();

  useEffect(() => {
    const params = new URLSearchParams(window.location.hash.slice(1));
    const token = params.get("token");
    if (!token) {
      navigate("/login", { replace: true });
      return;
    }
    setToken(token);
    const refreshToken = params.get("refresh");
    if (refreshToken) setRefreshToken(refreshToken);
    refresh().then(() => navigate("/", { replace: true }));
  }, []);

  return <div className="center-card">Signing you in…</div>;
}
