export interface WsClientOptions {
  onMessage: (event: { event_type: string; payload: unknown }) => void;
  onState: (state: "connecting" | "connected" | "reconnecting" | "closed") => void;
  onReconnect?: () => void;
}

const WS_BASE = import.meta.env.VITE_WS_BASE;

function resolveWsUrl(): string {
  if (WS_BASE) return WS_BASE;
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${window.location.host}/ws/events`;
}

export class WsClient {
  private ws: WebSocket | null = null;
  private reconnectTimer: number | null = null;
  private closedByUser = false;
  private reconnectAttempt = 0;

  constructor(private readonly opts: WsClientOptions) {}

  connect(): void {
    this.closedByUser = false;
    this.openSocket();
  }

  close(): void {
    this.closedByUser = true;
    if (this.reconnectTimer != null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.opts.onState("closed");
  }

  private openSocket(): void {
    this.opts.onState(this.reconnectAttempt > 0 ? "reconnecting" : "connecting");
    const ws = new WebSocket(resolveWsUrl());
    this.ws = ws;

    ws.onopen = () => {
      this.reconnectAttempt = 0;
      this.opts.onState("connected");
      this.opts.onReconnect?.();
    };

    ws.onmessage = (ev) => {
      try {
        const parsed = JSON.parse(ev.data) as { event_type: string; payload: unknown };
        this.opts.onMessage(parsed);
      } catch {
        // Ignore malformed payloads.
      }
    };

    ws.onclose = () => {
      if (this.closedByUser) return;
      this.scheduleReconnect();
    };

    ws.onerror = () => {
      if (this.closedByUser) return;
      ws.close();
    };
  }

  private scheduleReconnect(): void {
    this.reconnectAttempt += 1;
    const delay = Math.min(1000 * 2 ** this.reconnectAttempt, 10000);
    this.opts.onState("reconnecting");
    this.reconnectTimer = window.setTimeout(() => {
      this.openSocket();
    }, delay);
  }
}
