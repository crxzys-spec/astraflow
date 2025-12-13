declare module "event-source-polyfill" {
  type ExtendedEventSourceInit = EventSourceInit & { headers?: Record<string, string>; heartbeatTimeout?: number };

  // eslint-disable-next-line @typescript-eslint/no-extraneous-class
  export class EventSourcePolyfill extends EventSource {
    constructor(url: string | URL, eventSourceInitDict?: ExtendedEventSourceInit);
  }

  export default EventSourcePolyfill;
}
