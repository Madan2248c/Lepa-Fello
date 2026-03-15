"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { MessageSquare, X, Send, Loader2, ChevronRight } from "lucide-react";
import { useTenantId } from "@/hooks/useTenantId";
import { useAuth } from "@clerk/nextjs";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const SUGGESTIONS = [
  "Who are my highest intent accounts?",
  "Which visitors should I prioritize?",
  "Summarize my pipeline this week",
  "Who should I reach out to today?",
];

export default function AssistantSidebar({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const tenantId = useTenantId();
  const { getToken } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  const send = useCallback(async (text: string) => {
    if (!text.trim() || streaming) return;
    const userMsg: Message = { role: "user", content: text.trim() };
    const next = [...messages, userMsg];
    setMessages(next);
    setInput("");
    setStreaming(true);

    // Add empty assistant message to stream into
    setMessages(prev => [...prev, { role: "assistant", content: "" }]);

    try {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/assistant/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Tenant-Id": tenantId || "default",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ messages: next }),
      });

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data = line.slice(6);
          if (data === "[DONE]") break;
          try {
            const { text } = JSON.parse(data);
            if (text) {
              setMessages(prev => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  role: "assistant",
                  content: updated[updated.length - 1].content + text,
                };
                return updated;
              });
            }
          } catch {}
        }
      }
    } catch (e) {
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = { role: "assistant", content: "Sorry, something went wrong." };
        return updated;
      });
    } finally {
      setStreaming(false);
    }
  }, [messages, streaming, tenantId]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  };

  return (
    <div
      className={`flex flex-col h-screen bg-white border-l border-[#DDDDDD] transition-all duration-200 shrink-0 ${
        open ? "w-[380px]" : "w-0 overflow-hidden"
      }`}
    >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-[#DDDDDD] bg-[#F7F7F7]">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-[#FF5A5F] flex items-center justify-center">
                <MessageSquare className="w-3.5 h-3.5 text-white" />
              </div>
              <div>
                <p className="text-[13px] font-semibold text-[#484848]">LEPA Assistant</p>
                <p className="text-[11px] text-[#767676]">Ask anything about your pipeline</p>
              </div>
            </div>
            <button onClick={onClose} className="text-[#767676] hover:text-[#484848]">
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 && (
              <div className="space-y-3">
                <p className="text-[13px] text-[#767676] text-center mt-4">
                  Ask me anything about your accounts, visitors, or contacts.
                </p>
                <div className="space-y-2">
                  {SUGGESTIONS.map(s => (
                    <button
                      key={s}
                      onClick={() => send(s)}
                      className="w-full text-left flex items-center justify-between px-3 py-2.5 rounded-[6px] border border-[#DDDDDD] text-[13px] text-[#484848] hover:bg-[#F7F7F7] hover:border-[#FF5A5F] transition-colors group"
                    >
                      <span>{s}</span>
                      <ChevronRight className="w-3.5 h-3.5 text-[#767676] group-hover:text-[#FF5A5F]" />
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[85%] px-3 py-2.5 rounded-[8px] text-[13px] leading-relaxed whitespace-pre-wrap ${
                    m.role === "user"
                      ? "bg-[#484848] text-white"
                      : "bg-[#F7F7F7] text-[#484848] border border-[#eaf0f6]"
                  }`}
                >
                  {m.content}
                  {m.role === "assistant" && streaming && i === messages.length - 1 && m.content === "" && (
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-[#767676]" />
                  )}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="p-3 border-t border-[#DDDDDD]">
            <div className="flex items-end gap-2 bg-[#F7F7F7] border border-[#DDDDDD] rounded-[6px] px-3 py-2 focus-within:border-[#FF5A5F]">
              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about your pipeline..."
                rows={1}
                className="flex-1 bg-transparent text-[13px] text-[#484848] placeholder-[#b0c1d0] resize-none focus:outline-none max-h-32"
                style={{ minHeight: "20px" }}
              />
              <button
                onClick={() => send(input)}
                disabled={!input.trim() || streaming}
                className="text-[#FF5A5F] hover:text-[#e0504a] disabled:opacity-30 shrink-0 mb-0.5"
              >
                {streaming ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              </button>
            </div>
            <p className="text-[11px] text-[#b0c1d0] mt-1.5 text-center">Enter to send · Shift+Enter for new line</p>
          </div>
    </div>
  );
}
