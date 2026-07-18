import { useEffect, useState } from "react";
import { apiFetch } from "../api";

export default function Settings() {
  const [models, setModels] = useState([]);
  const [current, setCurrent] = useState(null);
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [status, setStatus] = useState("");

  useEffect(() => {
    apiFetch("/settings/models").then(setModels);
    apiFetch("/settings/llm").then((cfg) => {
      if (cfg) {
        setCurrent(cfg);
        setModel(cfg.model);
        setBaseUrl(cfg.base_url);
      }
    });
  }, []);

  const selected = models.find((m) => m.id === model);

  const save = async (e) => {
    e.preventDefault();
    setStatus("Saving…");
    try {
      const cfg = await apiFetch("/settings/llm", {
        method: "PUT",
        body: JSON.stringify({ provider: selected.provider, model, api_key: apiKey, base_url: baseUrl || null }),
      });
      setCurrent(cfg);
      setApiKey("");
      setStatus("Saved. You can start chatting now.");
    } catch (err) {
      setStatus(err.message);
    }
  };

  return (
    <div className="panel">
      <h2>LLM connection</h2>
      <p className="muted">
        Bring your own key — we never pre-load one. Pick a model, paste your provider API key, and start chatting.
      </p>

      {current && (
        <p className="pill">
          Currently connected: {current.model} ({current.provider}) — key set ✓
        </p>
      )}

      <form onSubmit={save} className="stack">
        <label>
          Model
          <select
            value={model}
            onChange={(e) => {
              setModel(e.target.value);
              setBaseUrl("");
            }}
            required
          >
            <option value="" disabled>
              Select a model
            </option>
            {models.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label} ({m.provider})
              </option>
            ))}
          </select>
        </label>

        <label>
          API key (one, or several comma-separated — requests rotate between them)
          <input
            type="password"
            placeholder={selected?.provider === "anthropic" ? "sk-ant-..." : "sk-..."}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            required
          />
        </label>

        <label>
          Base URL (optional override)
          <input placeholder="leave blank for provider default" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
        </label>

        <button className="btn btn-primary" disabled={!model || !apiKey}>
          Save
        </button>
      </form>

      {status && <p className="muted">{status}</p>}
    </div>
  );
}
