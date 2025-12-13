import { UiEventType, type UiEventEnvelope } from "../../client/models";
import { sseClient } from "./client";

type UiEventHandler = (event: UiEventEnvelope) => void;

const handlerMap = new Map<UiEventType, Set<UiEventHandler>>();

let unsubscribeFromClient: (() => void) | null = null;

const hasHandlers = (): boolean => {
  for (const set of handlerMap.values()) {
    if (set.size > 0) {
      return true;
    }
  }
  return false;
};

const dispatchEvent = (event: UiEventEnvelope) => {
  if (!event?.type) {
    return;
  }
  // Only dispatch known UiEventType values to guard against malformed payloads.
  if (!Object.values(UiEventType).includes(event.type)) {
    return;
  }
  const listeners = handlerMap.get(event.type as UiEventType);
  if (!listeners || listeners.size === 0) {
    return;
  }
  listeners.forEach((listener) => {
    try {
      listener(event);
    } catch (error) {
      // Never let a consumer break the SSE stream.
      console.error("SSE handler threw", error, event);
    }
  });
};

const ensureSubscribed = () => {
  if (unsubscribeFromClient) {
    return;
  }
  unsubscribeFromClient = sseClient.subscribe((event) => {
    dispatchEvent(event);
  });
};

const maybeTeardown = () => {
  if (unsubscribeFromClient && !hasHandlers()) {
    unsubscribeFromClient();
    unsubscribeFromClient = null;
  }
};

export const registerSseHandler = (type: UiEventType, handler: UiEventHandler): (() => void) => {
  ensureSubscribed();

  const listeners = handlerMap.get(type) ?? new Set<UiEventHandler>();
  listeners.add(handler);
  handlerMap.set(type, listeners);

  return () => {
    const existing = handlerMap.get(type);
    if (!existing) {
      return;
    }
    existing.delete(handler);
    if (existing.size === 0) {
      handlerMap.delete(type);
    }
    maybeTeardown();
  };
};

