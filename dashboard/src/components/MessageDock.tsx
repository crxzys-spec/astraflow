import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

export type MessageDockMessage = {
  id: string;
  content: ReactNode;
  durationMs?: number;
  tone?: "success" | "error" | "info";
};

type MessageDockProps = {
  messages: MessageDockMessage[];
  defaultDurationMs?: number;
  onDismiss?: (id: string) => void;
};

const MessageDock = ({ messages, defaultDurationMs = 6000, onDismiss }: MessageDockProps) => {
  const [active, setActive] = useState<MessageDockMessage[]>([]);
  const timers = useRef<Record<string, number>>({});

  useEffect(() => {
    setActive((prev) => {
      const knownIds = new Set(prev.map((item) => item.id));
      const next = [...prev];
      messages.forEach((msg) => {
        if (!knownIds.has(msg.id)) {
          next.push(msg);
        }
      });
      return next;
    });
  }, [messages]);

  useEffect(() => {
    active.forEach((msg) => {
      if (timers.current[msg.id]) {
        return;
      }
      const timeout = window.setTimeout(() => {
        setActive((prev) => prev.filter((item) => item.id !== msg.id));
        onDismiss?.(msg.id);
        window.clearTimeout(timeout);
        delete timers.current[msg.id];
      }, msg.durationMs ?? defaultDurationMs);
      timers.current[msg.id] = timeout;
    });
    return () => {
      Object.values(timers.current).forEach((id) => window.clearTimeout(id));
      timers.current = {};
    };
  }, [active, defaultDurationMs, onDismiss]);

  const dismiss = useCallback(
    (id: string) => {
      if (timers.current[id]) {
        window.clearTimeout(timers.current[id]);
        delete timers.current[id];
      }
      onDismiss?.(id);
      setActive((prev) => prev.filter((item) => item.id !== id));
    },
    [onDismiss]
  );

  if (!active.length) {
    return null;
  }

  return (
    <div className="message-dock" role="status" aria-live="polite">
      {active.map((message) => (
        <div
          key={message.id}
          className={`message-dock__item message-dock__item--${message.tone ?? "success"}`}
        >
          <span className="message-dock__halo" aria-hidden />
          <div className="message-dock__icon" aria-hidden>
            {message.tone === "error" ? (
              <svg viewBox="0 0 20 20" fill="none" aria-hidden focusable="false">
                <path
                  d="m5.5 5.5 9 9m-9 0 9-9"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>
            ) : (
              <svg viewBox="0 0 20 20" fill="none" aria-hidden focusable="false">
                <path
                  d="M15.833 5.833 8.75 12.917 4.167 8.333"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
          </div>
          <span className="message-dock__content">{message.content}</span>
          <button
            type="button"
            className="message-dock__close"
            aria-label="Dismiss message"
            onClick={() => dismiss(message.id)}
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
};

export default MessageDock;
