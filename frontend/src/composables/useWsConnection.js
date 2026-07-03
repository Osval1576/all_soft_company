import { ref, onMounted, onBeforeUnmount } from "vue";

const BACKOFFS_MS = [1000, 2000, 4000, 8000, 16000];

export function useWsConnection({ url, onMessage }) {
  const status = ref("connecting");
  let socket = null;
  let attempts = 0;
  let retryTimer = null;
  let closedByUser = false;
  let generation = 0;

  function connect() {
    if (socket && socket.readyState !== WebSocket.CLOSED) return;
    generation += 1;
    const myGen = generation;
    try {
      status.value = attempts === 0 ? "connecting" : "reconnecting";
      const target = typeof url === "function" ? url() : url;
      socket = new WebSocket(target);
    } catch (e) {
      scheduleRetry(myGen);
      return;
    }

    socket.onopen = () => {
      if (myGen !== generation) return;
      attempts = 0;
      status.value = "connected";
    };
    socket.onmessage = (evt) => {
      if (myGen !== generation) return;
      try {
        const parsed = JSON.parse(evt.data);
        if (onMessage) onMessage(parsed);
      } catch (_) {}
    };
    socket.onerror = () => {};
    socket.onclose = () => {
      if (myGen !== generation) return;
      if (closedByUser) return;
      scheduleRetry(myGen);
    };
  }

  function scheduleRetry(fromGen) {
    if (fromGen !== generation) return;
    if (attempts >= BACKOFFS_MS.length) {
      status.value = "disconnected";
      return;
    }
    status.value = "reconnecting";
    const wait = BACKOFFS_MS[attempts];
    attempts += 1;
    retryTimer = setTimeout(() => { if (fromGen === generation) connect(); }, wait);
  }

  function send(payload) {
    if (!socket || socket.readyState !== WebSocket.OPEN) return false;
    socket.send(typeof payload === "string" ? payload : JSON.stringify(payload));
    return true;
  }

  function close() {
    closedByUser = true;
    generation += 1;
    if (retryTimer) clearTimeout(retryTimer);
    if (socket) { try { socket.close(); } catch (_) {} }
    socket = null;
  }

  function retry() {
    if (retryTimer) clearTimeout(retryTimer);
    attempts = 0;
    closedByUser = false;
    connect();
  }

  onMounted(connect);
  onBeforeUnmount(close);

  return { status, send, close, retry };
}
