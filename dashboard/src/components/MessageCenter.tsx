import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import MessageDock from "./MessageDock";

export type MessageTone = "success" | "error" | "info";

export type MessagePayload = {
  id?: string;
  content: ReactNode;
  durationMs?: number;
  tone?: MessageTone;
};

type MessageEntry = Required<Pick<MessagePayload, "content">> & {
  id: string;
  durationMs?: number;
  tone?: MessageTone;
};

type MessageCenterValue = {
  pushMessage: (message: MessagePayload) => string;
  dismissMessage: (id: string) => void;
};

const MessageCenterContext = createContext<MessageCenterValue | null>(null);

const generateId = () =>
  typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `msg-${Date.now()}-${Math.random().toString(16).slice(2)}`;

export const MessageProvider = ({
  children,
  defaultDurationMs = 6000,
}: {
  children: ReactNode;
  defaultDurationMs?: number;
}) => {
  const [messages, setMessages] = useState<MessageEntry[]>([]);

  const pushMessage = useCallback(
    ({ id, ...rest }: MessagePayload) => {
      const nextId = id ?? generateId();
      setMessages((prev) => {
        if (prev.some((item) => item.id === nextId)) {
          return prev;
        }
        return [...prev, { id: nextId, ...rest }];
      });
      return nextId;
    },
    []
  );

  const dismissMessage = useCallback((id: string) => {
    setMessages((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const value = useMemo(
    () => ({
      pushMessage,
      dismissMessage,
    }),
    [dismissMessage, pushMessage]
  );

  return (
    <MessageCenterContext.Provider value={value}>
      {children}
      <MessageDock
        messages={messages}
        defaultDurationMs={defaultDurationMs}
        onDismiss={dismissMessage}
      />
    </MessageCenterContext.Provider>
  );
};

export const useMessageCenter = () => {
  const ctx = useContext(MessageCenterContext);
  if (!ctx) {
    throw new Error("useMessageCenter must be used within a MessageProvider");
  }
  return ctx;
};
