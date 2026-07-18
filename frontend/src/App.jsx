import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./AuthContext";
import Layout from "./Layout";
import Login from "./pages/Login";
import AuthCallback from "./pages/AuthCallback";
import Paywall from "./pages/Paywall";
import Chat from "./pages/Chat";
import Settings from "./pages/Settings";
import Stats from "./pages/Stats";
import Admin from "./pages/Admin";

function PaywallRoute() {
  const { me, loading } = useAuth();
  if (loading) return <div className="center-card">Loading…</div>;
  if (!me) return <Navigate to="/login" replace />;
  if (me.has_access) return <Navigate to="/chat" replace />;
  return <Paywall />;
}

function LoginRoute() {
  const { me, loading } = useAuth();
  if (loading) return <div className="center-card">Loading…</div>;
  if (me) return <Navigate to={me.has_access ? "/chat" : "/paywall"} replace />;
  return <Login />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginRoute />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      <Route path="/paywall" element={<PaywallRoute />} />
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/chat" replace />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/chat/:threadId" element={<Chat />} />
        <Route path="/stats" element={<Stats />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/admin" element={<Admin />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
