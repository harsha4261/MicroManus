import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { apiFetch, apiStream, downloadPdf } from "../api";
import { confirmDialog, toastError } from "../alert";
import { t } from "../i18n";
import { useAuth } from "../AuthContext";

function AssistantBubble({ threadId, messageId, content }) {
  const exportable = messageId && !messageId.startsWith("pending");
  return (
    <div className="bubble assistant">
      <div className="markdown">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      </div>
      {exportable && (
        <button className="btn-link" onClick={() => downloadPdf(threadId, messageId).catch((e) => toastError(e.message))}>
          {t("downloadPdf")}
        </button>
      )}
    </div>
  );
}

function TraceStep({ event }) {
  if (event.type === "tool_call") {
    const isSearch = event.name === "web_search";
    return (
      <div className="trace-step">
        <span className="trace-verb">{isSearch ? "search" : "read"}</span>
        {isSearch ? event.args.query : event.args.url}
      </div>
    );
  }
  if (event.type === "tool_result")
    return (
      <div className="trace-step">
        <span className="trace-verb">found</span>
        {event.content.slice(0, 160)}
      </div>
    );
  return null;
}

export default function Chat() {
  const { threadId } = useParams();
  const navigate = useNavigate();
  const { me, refresh } = useAuth();
  const [threads, setThreads] = useState([]);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [trace, setTrace] = useState([]);
  const [streamText, setStreamText] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef(null);

  const loadThreads = async () => setThreads(await apiFetch("/threads"));

  useEffect(() => {
    loadThreads();
  }, []);

  useEffect(() => {
    if (threadId) apiFetch(`/threads/${threadId}/messages`).then(setMessages);
    else setMessages([]);
  }, [threadId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, trace, streamText]);

  const buyCredits = async () => {
    try {
      const { url } = await apiFetch("/billing/checkout", { method: "POST" });
      window.location.href = url;
    } catch (err) {
      toastError(err.message);
    }
  };

  const offerCredits = async () => {
    if (await confirmDialog({ title: t("outOfCredits"), text: t("outOfCreditsText"), confirmText: t("buyCredits") })) {
      buyCredits();
    }
  };

  const newChat = async () => {
    try {
      const thread = await apiFetch("/threads", { method: "POST" });
      await loadThreads();
      navigate(`/chat/${thread.id}`);
    } catch (err) {
      toastError(err.message);
    }
  };

  const deleteThread = async (e, id) => {
    e.stopPropagation();
    if (!(await confirmDialog({ title: t("deleteConfirmTitle"), text: t("deleteConfirmText"), confirmText: t("delete") }))) return;
    try {
      await apiFetch(`/threads/${id}`, { method: "DELETE" });
      await loadThreads();
      if (id === threadId) navigate("/chat");
    } catch (err) {
      toastError(err.message);
    }
  };

  const send = async (e) => {
    e.preventDefault();
    if (!input.trim() || sending) return;
    if (me?.credits === 0) {
      offerCredits();
      return;
    }
    const content = input;
    setInput("");
    setMessages((prev) => [...prev, { id: "pending-user", role: "user", content }]);
    setTrace([]);
    setSending(true);

    try {
      const res = await apiStream(`/threads/${threadId}/messages`, { content });
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        if (res.status === 402) {
          offerCredits();
          return;
        }
        throw new Error(body.detail || "Request failed");
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const chunks = buffer.split("\n\n");
        buffer = chunks.pop();
        for (const chunk of chunks) {
          if (!chunk.startsWith("data: ")) continue;
          const event = JSON.parse(chunk.slice(6));
          if (event.type === "delta") {
            setStreamText((prev) => prev + event.content);
          } else if (event.type === "tool_call" || event.type === "tool_result") {
            setStreamText(""); // a new agent turn began; drop any pre-tool-call thinking text
            setTrace((prev) => [...prev, event]);
          } else if (event.type === "answer") {
            setMessages((prev) => [...prev, { id: "pending-assistant", role: "assistant", content: event.content }]);
            setStreamText("");
            setTrace([]);
          } else if (event.type === "error") {
            toastError(event.content);
          }
        }
      }
    } catch (err) {
      toastError(err.message);
    } finally {
      setSending(false);
      setTrace([]);
      setStreamText("");
      const [freshMessages] = await Promise.all([apiFetch(`/threads/${threadId}/messages`), loadThreads(), refresh()]);
      setMessages(freshMessages);
    }
  };

  return (
    <div className="chat-layout">
      <aside className="sidebar">
        <button className="btn btn-primary" onClick={newChat}>
          {t("newChat")}
        </button>
        <div className="thread-list">
          {threads.map((th) => (
            <div
              key={th.id}
              className={`thread-item ${th.id === threadId ? "active" : ""}`}
              onClick={() => navigate(`/chat/${th.id}`)}
            >
              <span className="thread-title">{th.title}</span>
              <button className="thread-delete" title={t("deleteChat")} onClick={(e) => deleteThread(e, th.id)}>
                ×
              </button>
            </div>
          ))}
        </div>
        <div className="credits-pill">
          {me?.credits ?? 0} {t("creditsLeft")}
          {me?.credits === 0 && (
            <button className="btn-link" onClick={buyCredits}>
              {t("buyCredits")}
            </button>
          )}
        </div>
      </aside>

      <main className="chat-main">
        {!threadId && (
          <div className="empty-state">
            <h2>{t("emptyTitle")}</h2>
            <p className="muted">{t("emptyBody")}</p>
            <p className="muted">
              Try: "Create a report explaining the recent forest fires in California, what's causing them, and what can
              be done to avoid it."
            </p>
          </div>
        )}

        {threadId && (
          <>
            <div className="messages">
              {messages.map((m) =>
                m.role === "assistant" ? (
                  <AssistantBubble key={m.id} threadId={threadId} messageId={m.id} content={m.content} />
                ) : (
                  <div key={m.id} className="bubble user">
                    {m.content}
                  </div>
                )
              )}
              {trace.map((event, i) => (
                <TraceStep key={i} event={event} />
              ))}
              {streamText && (
                <div className="bubble assistant">
                  <div className="markdown">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{streamText}</ReactMarkdown>
                  </div>
                </div>
              )}
              {sending && !streamText && (
                <div className="trace-step thinking">
                  <span className="trace-verb">think</span>
                  {t("thinking")}
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            <form className="composer" onSubmit={send}>
              <input placeholder={t("ask")} value={input} onChange={(e) => setInput(e.target.value)} disabled={sending} />
              <button className="btn btn-primary" disabled={sending || !input.trim()}>
                {t("send")}
              </button>
            </form>
          </>
        )}
      </main>
    </div>
  );
}
