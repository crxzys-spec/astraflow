import { EventSourcePolyfill } from "event-source-polyfill";
import { UiEventType, type UiEventEnvelope } from "../../client/models";
import { getClientSessionId } from "../clientSession";
import { getAuthToken } from "../setupAxios";

type UiEventListener = (event: UiEventEnvelope) => void;
export type SseConnectionStatus = "idle" | "connecting" | "open" | "reconnecting";
type SseStatusListener = (status: SseConnectionStatus) => void;

const DEFAULT_RETRY_MS = 2_000;
const MAX_RETRY_MS = 60_000;
const HEARTBEAT_TIMEOUT_MS = 120_000;

const buildEventsUrl = (clientSessionId: string): string => {
  const envBase = import.meta.env.VITE_SCHEDULER_BASE_URL;
  let base: URL;
  if (envBase) {
    try {
      const parsed = new URL(envBase, window.location.origin);
      if (parsed.origin !== window.location.origin && import.meta.env.DEV) {
        // In dev prefer proxy to avoid CORS trouble.
        base = new URL(window.location.origin);
      } else {
        base = parsed;
      }
    } catch (error) {
      console.warn("[sse] Invalid VITE_SCHEDULER_BASE_URL, falling back to window origin", error);
      base = new URL(window.location.origin);
    }
  } else {
    base = new URL(window.location.origin);
  }

  base.pathname = "/api/v1/events";
  base.searchParams.set("clientSessionId", clientSessionId);

  return base.toString();
};

export class SseClient {
  private listeners = new Set<UiEventListener>();
  private statusListeners = new Set<SseStatusListener>();
  private eventSource: EventSource | null = null;
  private reconnectTimer: number | null = null;
  private retryDelay = DEFAULT_RETRY_MS;
  private connecting = false;
  private keepAlive = false;
  private status: SseConnectionStatus = "idle";

  subscribe(listener: UiEventListener): () => void {
    this.listeners.add(listener);
    this.ensureConnection();

    return () => {
      this.listeners.delete(listener);
      if (this.listeners.size === 0 && !this.keepAlive) {
        this.teardown();
      }
    };
  }

  subscribeStatus(listener: SseStatusListener): () => void {
    this.statusListeners.add(listener);
    listener(this.status);
    return () => {
      this.statusListeners.delete(listener);
    };
  }

  enableKeepAlive(): void {
    if (this.keepAlive) {
      return;
    }
    this.keepAlive = true;
    this.ensureConnection(true);
  }

  disableKeepAlive(): void {
    this.keepAlive = false;
    if (this.listeners.size === 0) {
      this.teardown();
    }
  }

  private ensureConnection(force = false) {
    if (this.eventSource || this.connecting) {
      return;
    }
    if (!force && !this.keepAlive && this.listeners.size === 0) {
      return;
    }
    this.connect();
  }

  private setStatus(next: SseConnectionStatus) {
    if (this.status === next) {
      return;
    }
    this.status = next;
    this.statusListeners.forEach((listener) => listener(next));
  }

  private connect() {
    this.connecting = true;
    this.setStatus("connecting");
    const sessionId = getClientSessionId();
    const url = buildEventsUrl(sessionId);

    try {
      const authToken = getAuthToken() ?? import.meta.env.VITE_SCHEDULER_TOKEN ?? "dev-token";
      const eventSource = new EventSourcePolyfill(url, {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
        withCredentials: true,
        heartbeatTimeout: HEARTBEAT_TIMEOUT_MS,
      });
      this.eventSource = eventSource;

      const handleEvent = (evt: MessageEvent<string>) => {
        this.handleIncomingEvent(evt.data);
      };

      Object.values(UiEventType).forEach((eventName) => {
        eventSource.addEventListener(eventName, handleEvent as EventListener);
      });

      eventSource.onopen = () => {
        this.retryDelay = DEFAULT_RETRY_MS;
        if (this.reconnectTimer !== null) {
          window.clearTimeout(this.reconnectTimer);
          this.reconnectTimer = null;
        }
        this.setStatus("open");
      };

      eventSource.onerror = () => {
        this.scheduleReconnect();
      };
    } catch (error) {
      console.warn("Unable to establish SSE connection", error);
      this.scheduleReconnect();
    } finally {
      this.connecting = false;
    }
  }

  private handleIncomingEvent(rawPayload: string) {
    let envelope: UiEventEnvelope | null = null;
    try {
      envelope = JSON.parse(rawPayload) as UiEventEnvelope;
    } catch (error) {
      console.warn("Failed to parse SSE payload", rawPayload, error);
      return;
    }

    this.listeners.forEach((listener) => {
      try {
        listener(envelope as UiEventEnvelope);
      } catch (error) {
        console.error("SSE listener threw", error);
      }
    });
  }

  private scheduleReconnect() {
    if (!this.keepAlive && this.listeners.size === 0) {
      this.teardown();
      return;
    }

    this.cleanupConnection();
    this.setStatus("reconnecting");
    if (this.reconnectTimer !== null) {
      return;
    }

    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      this.retryDelay = Math.min(this.retryDelay * 2, MAX_RETRY_MS);
      this.connect();
    }, this.retryDelay);
  }

  private teardown() {
    this.cleanupConnection();
    this.setStatus("idle");
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.retryDelay = DEFAULT_RETRY_MS;
  }

  private cleanupConnection() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}

export const sseClient = new SseClient();
