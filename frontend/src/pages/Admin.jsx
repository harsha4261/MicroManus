import { useEffect, useState } from "react";
import { apiFetch } from "../api";
import { toastError } from "../alert";

export default function Admin() {
  const [users, setUsers] = useState([]);

  const load = () => apiFetch("/admin/users").then(setUsers).catch((e) => toastError(e.message));

  useEffect(() => {
    load();
  }, []);

  const adjust = async (id, delta) => {
    try {
      await apiFetch(`/admin/users/${id}/credits`, { method: "POST", body: JSON.stringify({ delta }) });
      load();
    } catch (e) {
      toastError(e.message);
    }
  };

  return (
    <div className="panel">
      <h2>Admin</h2>
      <p className="muted">Every account, its balance, and what it has paid.</p>
      <table className="stats-table">
        <thead>
          <tr>
            <th>Email</th>
            <th>Credits</th>
            <th>Chats</th>
            <th>Paid</th>
            <th>Coupon</th>
            <th>Adjust</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id}>
              <td>{u.email}</td>
              <td>{u.credits}</td>
              <td>{u.threads}</td>
              <td>${u.paid_usd.toFixed(2)}</td>
              <td>{u.coupon_redeemed ? "yes" : "—"}</td>
              <td>
                <button className="btn-link" onClick={() => adjust(u.id, 5)}>
                  +5
                </button>{" "}
                <button className="btn-link" onClick={() => adjust(u.id, -5)}>
                  −5
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
