import { useEffect, useState } from "react";
import { apiFetch } from "../api";

export default function Stats() {
  const [rows, setRows] = useState([]);

  useEffect(() => {
    apiFetch("/stats").then(setRows);
  }, []);

  const totals = rows.reduce(
    (acc, r) => ({
      messages: acc.messages + r.message_count,
      input: acc.input + r.input_tokens,
      output: acc.output + r.output_tokens,
      cacheRead: acc.cacheRead + r.cache_read_tokens,
      cacheWrite: acc.cacheWrite + r.cache_write_tokens,
      cost: acc.cost + r.cost_usd,
    }),
    { messages: 0, input: 0, output: 0, cacheRead: 0, cacheWrite: 0, cost: 0 }
  );

  return (
    <div className="panel">
      <h2>Cost & stats</h2>
      <table className="stats-table">
        <thead>
          <tr>
            <th>Chat</th>
            <th>Model</th>
            <th>Msgs</th>
            <th>Input tok</th>
            <th>Output tok</th>
            <th>Cache read</th>
            <th>Cache write</th>
            <th>Cost</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.thread_id}>
              <td>{r.title}</td>
              <td>{r.model}</td>
              <td>{r.message_count}</td>
              <td>{r.input_tokens.toLocaleString()}</td>
              <td>{r.output_tokens.toLocaleString()}</td>
              <td>{r.cache_read_tokens.toLocaleString()}</td>
              <td>{r.cache_write_tokens.toLocaleString()}</td>
              <td>${r.cost_usd.toFixed(4)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td colSpan={2}>
              <strong>Total</strong>
            </td>
            <td>{totals.messages}</td>
            <td>{totals.input.toLocaleString()}</td>
            <td>{totals.output.toLocaleString()}</td>
            <td>{totals.cacheRead.toLocaleString()}</td>
            <td>{totals.cacheWrite.toLocaleString()}</td>
            <td>${totals.cost.toFixed(4)}</td>
          </tr>
        </tfoot>
      </table>
      {rows.length === 0 && <p className="muted">No chats yet.</p>}
    </div>
  );
}
