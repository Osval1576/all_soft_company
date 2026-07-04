import { defineStore } from "pinia";
import {
  listNotifications,
  markRead as apiMarkRead,
  markAllRead as apiMarkAllRead,
} from "../api/notifications.api";

const BACKOFFS_MS = [1000, 2000, 4000, 8000, 16000];

let socket = null;
let attempts = 0;
let retryTimer = null;
let pingTimer = null;
let closedByUser = false;
let toastSeq = 0;

export const useNotificationsStore = defineStore("notifications", {
  state: () => ({
    connected: false,
    unreadCount: 0,
    items: [],
    toasts: [],
    activeTicketId: null,
  }),

  actions: {
    async init() {
      await this.loadHistory();
      this.connect();
    },

    async loadHistory() {
      try {
        const data = await listNotifications();
        this.items = data;
        this.unreadCount = data.filter((n) => !n.is_read).length;
      } catch (_) {}
    },

    connect() {
      if (socket && socket.readyState !== WebSocket.CLOSED) return;
      closedByUser = false;
      const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = import.meta.env.VITE_WS_HOST || window.location.host;
      let s;
      try {
        s = new WebSocket(`${proto}//${host}/ws/notify/`);
      } catch (_) {
        this._scheduleRetry();
        return;
      }
      socket = s;
      s.onopen = () => {
        this.connected = true;
        attempts = 0;
        this._startPing();
      };
      s.onmessage = (evt) => {
        try {
          this._onMessage(JSON.parse(evt.data));
        } catch (_) {}
      };
      s.onclose = () => {
        this.connected = false;
        this._stopPing();
        if (!closedByUser) this._scheduleRetry();
      };
      s.onerror = () => {};
    },

    _onMessage(n) {
      this.items.unshift(n);
      if (!n.is_read) this.unreadCount += 1;
      // Suprimir el toast del ticket que el usuario está mirando (ya lo ve en vivo).
      if (n.kind === "new_message" && n.ticket && n.ticket === this.activeTicketId) return;
      this._pushToast(n);
    },

    _pushToast(n) {
      const id = ++toastSeq;
      this.toasts.push({ toastId: id, ...n });
      setTimeout(() => this.dismissToast(id), 5000);
    },

    dismissToast(id) {
      this.toasts = this.toasts.filter((t) => t.toastId !== id);
    },

    setActiveTicket(id) {
      this.activeTicketId = id;
    },

    async markRead(id) {
      const n = this.items.find((x) => x.id === id);
      if (n && !n.is_read) {
        n.is_read = true;
        this.unreadCount = Math.max(0, this.unreadCount - 1);
      }
      try {
        await apiMarkRead(id);
      } catch (_) {}
    },

    async markAllRead() {
      this.items.forEach((n) => (n.is_read = true));
      this.unreadCount = 0;
      try {
        await apiMarkAllRead();
      } catch (_) {}
    },

    _startPing() {
      this._stopPing();
      pingTimer = setInterval(() => {
        if (socket && socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: "ping" }));
        }
      }, 30000);
    },

    _stopPing() {
      if (pingTimer) {
        clearInterval(pingTimer);
        pingTimer = null;
      }
    },

    _scheduleRetry() {
      if (attempts >= BACKOFFS_MS.length) return;
      const wait = BACKOFFS_MS[attempts++];
      retryTimer = setTimeout(() => this.connect(), wait);
    },

    disconnect() {
      closedByUser = true;
      this._stopPing();
      if (retryTimer) clearTimeout(retryTimer);
      if (socket) {
        try {
          socket.close();
        } catch (_) {}
      }
      socket = null;
      attempts = 0;
      this.connected = false;
      this.unreadCount = 0;
      this.items = [];
      this.toasts = [];
      this.activeTicketId = null;
    },
  },
});
