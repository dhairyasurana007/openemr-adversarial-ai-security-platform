import { useMutation } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { fireManualAttack } from "../api/service";

interface Message {
  id: string;
  role: "user" | "assistant" | "error";
  content: string;
  timestamp: Date;
  statusCode?: number;
}

function extractText(response: unknown): string {
  if (typeof response === "string") return response;
  if (response && typeof response === "object") {
    const r = response as Record<string, unknown>;
    if (typeof r.message === "string") return r.message;
    if (typeof r.content === "string") return r.content;
    if (typeof r.text === "string") return r.text;
    if (typeof r.response === "string") return r.response;
    if (Array.isArray(r.choices) && r.choices.length > 0) {
      const choice = r.choices[0] as Record<string, unknown>;
      if (choice.message) {
        const msg = choice.message as Record<string, unknown>;
        if (typeof msg.content === "string") return msg.content;
      }
      if (typeof choice.text === "string") return choice.text;
    }
  }
  return JSON.stringify(response, null, 2);
}

interface Props {
  targetUrl: string;
  sessionId?: string;
}

export function ChatInterface({ targetUrl, sessionId }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const sendMutation = useMutation({
    mutationFn: (msg: string) =>
      fireManualAttack({ message: msg, surface: "chat", use_rag: true, session_id: sessionId }),
    onSuccess: (data) => {
      setMessages((prev) => [
        ...prev,
        {
          id: `${Date.now()}-res`,
          role: "assistant",
          content: extractText(data.response),
          timestamp: new Date(),
          statusCode: data.status_code,
        },
      ]);
    },
    onError: (err) => {
      setMessages((prev) => [
        ...prev,
        {
          id: `${Date.now()}-err`,
          role: "error",
          content: err instanceof Error ? err.message : "Request failed",
          timestamp: new Date(),
        },
      ]);
    },
  });

  const send = () => {
    const msg = input.trim();
    if (!msg || sendMutation.isPending) return;
    setMessages((prev) => [
      ...prev,
      { id: `${Date.now()}-user`, role: "user", content: msg, timestamp: new Date() },
    ]);
    setInput("");
    sendMutation.mutate(msg);
  };

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, sendMutation.isPending]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="card" style={{ display: "flex", flexDirection: "column" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
        <div className="card-title" style={{ marginBottom: 0 }}>Target Interaction</div>
        <span className="font-mono" style={{ color: "var(--text-muted)" }}>{targetUrl}</span>
      </div>

      <div
        ref={scrollRef}
        style={{
          height: "55vh",
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: "0.75rem",
          paddingRight: "0.25rem",
        }}
      >
        {messages.length === 0 && !sendMutation.isPending && (
          <div className="empty" style={{ margin: "auto" }}>
            <div className="empty-icon">💬</div>
            <div className="empty-text">Send a message to interact with the target</div>
          </div>
        )}

        {messages.map((msg) => {
          const isUser = msg.role === "user";
          const isError = msg.role === "error";
          return (
            <div key={msg.id} style={{ alignSelf: isUser ? "flex-end" : "flex-start", maxWidth: "80%" }}>
              <div
                style={{
                  borderRadius: 14,
                  padding: "0.65rem 0.8rem",
                  background: isUser ? "var(--primary)" : isError ? "var(--danger-dim)" : "var(--surface)",
                  color: isUser ? "#fff" : isError ? "var(--danger)" : "var(--text)",
                  border: isUser ? "none" : `1px solid ${isError ? "var(--danger)" : "var(--border)"}`,
                }}
              >
                <div className="text-sm" style={{ fontWeight: 600, marginBottom: "0.2rem", opacity: 0.75 }}>
                  {isUser ? "You" : isError ? "Error" : "Target"}
                </div>
                <div style={{ fontSize: 13.5, lineHeight: 1.6, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                  {msg.content}
                </div>
              </div>
              <div
                className="text-sm"
                style={{ marginTop: "0.2rem", color: "var(--text-muted)", textAlign: isUser ? "right" : "left" }}
              >
                {msg.timestamp.toLocaleTimeString()}
                {msg.statusCode !== undefined ? ` • HTTP ${msg.statusCode}` : ""}
              </div>
            </div>
          );
        })}

        {sendMutation.isPending && (
          <div style={{ alignSelf: "flex-start" }}>
            <div
              style={{
                borderRadius: 14,
                padding: "0.65rem 0.8rem",
                background: "var(--surface)",
                border: "1px solid var(--border)",
                color: "var(--text-muted)",
                fontStyle: "italic",
              }}
            >
              Thinking...
            </div>
          </div>
        )}
      </div>

      <div
        style={{
          display: "flex",
          gap: "0.5rem",
          marginTop: "0.75rem",
          paddingTop: "0.75rem",
          borderTop: "1px solid var(--border)",
          alignItems: "flex-end",
        }}
      >
        <textarea
          className="form-textarea"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message... (Enter to send, Shift+Enter for new line)"
          rows={2}
          style={{ flex: 1, resize: "none", minHeight: "unset", fontFamily: "inherit", fontSize: "13.5px" }}
          disabled={sendMutation.isPending}
        />
        <button
          type="button"
          className="btn btn-primary"
          onClick={send}
          disabled={!input.trim() || sendMutation.isPending}
        >
          {sendMutation.isPending ? "Sending..." : "Send"}
        </button>
      </div>
    </div>
  );
}
