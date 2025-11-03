import { UiEventType } from "../api/models/uiEventType";
import type { UiEventEnvelope } from "../api/models/uiEventEnvelope";
import { getClientSessionId } from "./clientSession";

type UiEventListener = (event: UiEventEnvelope) => void;

const DEFAULT_RETRY_MS = 2_000;
const MAX_RETRY_MS = 60_000;

const buildEventsUrl = (clientSessionId: string): string => {
  const base =
    import.meta.env.VITE_SCHEDULER_BASE_URL != null
      ? new URL(import.meta.env.VITE_SCHEDULER_BASE_URL)
      : new URL(window.location.origin);

  base.pathname = "/api/v1/events";
  base.searchParams.set("clientSessionId", clientSessionId);

  return base.toString();
};

export class SseClient {
  private listeners = new Set<UiEventListener>();
  private eventSource: EventSource | null = null;
  private reconnectTimer: number | null = null;
  private retryDelay = DEFAULT_RETRY_MS;
  private connecting = false;
  private keepAlive = false;

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

  private connect() {
    this.connecting = true;
    const sessionId = getClientSessionId();
    const url = buildEventsUrl(sessionId);

    try {
      const source = new EventSource(url);
      this.eventSource = source;

      const handleEvent = (evt: MessageEvent<string>) => {
        this.handleIncomingEvent(evt.data);
      };

      Object.values(UiEventType).forEach((eventName) => {
        source.addEventListener(eventName, handleEvent as EventListener);
      });

      source.onopen = () => {
        this.retryDelay = DEFAULT_RETRY_MS;
        if (this.reconnectTimer !== null) {
          window.clearTimeout(this.reconnectTimer);
          this.reconnectTimer = null;
        }
      };

      source.onerror = () => {
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
