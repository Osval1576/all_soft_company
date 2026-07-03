<template>
  <div class="panel">
    <header v-if="showHeader" class="panel-header">
      <div class="header-info">
        <span class="header-title">{{ title }}</span>
        <div class="header-meta">
          <span class="conn-badge" :class="`conn-badge--${wsStatus}`">
            <span class="conn-dot" aria-hidden="true"></span>
            <span>{{ CONN_LABEL[wsStatus] || wsStatus }}</span>
          </span>
          <button
            v-if="wsStatus === 'disconnected'"
            @click="wsRetry"
            class="btn-retry"
          >Reintentar</button>
        </div>
      </div>
      <div v-if="status && canUpdateStatus" class="status-control">
        <select :value="status" @change="$emit('update:status', $event.target.value)" class="status-select">
          <option value="OPEN">Abierto</option>
          <option value="IN_PROGRESS">En proceso</option>
          <option value="RESOLVED">Resuelto</option>
          <option value="CLOSED">Cerrado</option>
        </select>
      </div>
    </header>

    <section class="messages" ref="messagesEl">
      <div v-if="loading" class="loading-state">Cargando mensajes...</div>

      <template v-else>
        <div v-if="messages.length === 0" class="empty-messages">
          No hay mensajes aún. Sé el primero en escribir.
        </div>

        <div
          v-for="m in messages"
          :key="m.id"
          class="msg-row"
          :class="m.sender_username === me ? 'msg-row--me' : 'msg-row--other'"
        >
          <div class="bubble">
            <div class="bubble-meta">
              <span v-if="m.sender_username !== me" class="bubble-sender">{{ m.sender_username }}</span>
              <span class="bubble-time">{{ formatTime(m.created_at) }}</span>
            </div>
            <div class="bubble-content">{{ m.content }}</div>
          </div>
        </div>
      </template>
    </section>

    <footer class="composer">
      <input
        v-model="draft"
        @keydown.enter.prevent="send"
        :placeholder="composerPlaceholder"
        class="composer-input"
        :disabled="wsStatus === 'disconnected'"
      />
      <button
        @click="send"
        :disabled="!draft.trim() || wsStatus !== 'connected'"
        class="composer-btn"
      >Enviar</button>
    </footer>

    <TicketEventTimeline :events="events" />
  </div>
</template>

<script setup>
import { nextTick, ref, watch, computed } from "vue";
import { getTicketMessages, getTicketEvents } from "../api/tickets.api";
import { useAuthStore } from "../stores/auth.store";
import { useWsConnection } from "../composables/useWsConnection";
import TicketEventTimeline from "./tickets/TicketEventTimeline.vue";

const props = defineProps({
  ticketId:        { type: Number, required: true },
  title:           { type: String, default: "" },
  showHeader:      { type: Boolean, default: true },
  status:          { type: String, default: null },
  canUpdateStatus: { type: Boolean, default: false },
});

defineEmits(["update:status"]);

const auth = useAuthStore();
const me   = computed(() => auth.user?.username);

const messages = ref([]);
const events = ref([]);
const loading = ref(false);
const draft = ref("");
const messagesEl = ref(null);

const CONN_LABEL = {
  connecting: "Conectando…",
  connected: "Conectado",
  reconnecting: "Reconectando…",
  disconnected: "Desconectado",
};

const composerPlaceholder = computed(() =>
  wsStatus.value === "connected" ? "Escribe un mensaje..." : "Chat desconectado"
);

function scrollToBottom() {
  if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight;
}

function formatTime(iso) {
  try {
    return new Date(iso).toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" });
  } catch { return iso; }
}

function wsUrl() {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = import.meta.env.VITE_WS_HOST || window.location.host;
  return `${proto}//${host}/ws/chat/${props.ticketId}/`;
}

const { status: wsStatus, send: wsSend, retry: wsRetry, close: wsClose } = useWsConnection({
  url: wsUrl,
  onMessage: async (m) => {
    messages.value.push(m);
    await nextTick();
    scrollToBottom();
  },
});

async function loadAll() {
  loading.value = true;
  try {
    const [msgs, evts] = await Promise.all([
      getTicketMessages(props.ticketId),
      getTicketEvents(props.ticketId).catch(() => []),
    ]);
    messages.value = msgs;
    events.value = evts;
    await nextTick();
    scrollToBottom();
  } finally {
    loading.value = false;
  }
}

function send() {
  const text = draft.value.trim();
  if (!text) return;
  if (wsSend({ content: text })) {
    draft.value = "";
  }
}

watch(() => props.ticketId, async () => {
  wsClose();
  await loadAll();
  wsRetry();
}, { immediate: true });
</script>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--surface);
  border-radius: var(--r);
  overflow: hidden;
  border: 0.5px solid var(--border);
}
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 0.5px solid var(--border);
  flex-shrink: 0;
  gap: 12px;
}
.header-info { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.header-title {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 14px;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.header-meta { display: flex; align-items: center; gap: 10px; }
.conn-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--text-3);
}
.conn-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--text-3); }
.conn-badge--connected .conn-dot { background: var(--c-resolved, #10B981); box-shadow: 0 0 0 3px rgba(16,185,129,.15); }
.conn-badge--connected { color: var(--c-resolved, #10B981); }
.conn-badge--connecting .conn-dot,
.conn-badge--reconnecting .conn-dot {
  background: var(--c-open, #F59E0B);
  animation: conn-pulse 1s ease-in-out infinite;
}
.conn-badge--connecting,
.conn-badge--reconnecting { color: var(--c-open, #F59E0B); }
@keyframes conn-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
.btn-retry {
  padding: 4px 10px;
  border: 0.5px solid var(--border);
  border-radius: 4px;
  background: transparent;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--accent);
  cursor: pointer;
}
[data-theme="dark"] .btn-retry { color: var(--accent-2); }
.status-select {
  padding: 4px 10px;
  border: 0.5px solid var(--border);
  border-radius: var(--r-sm);
  background: var(--surface-2);
  color: var(--text);
  font-size: 12px;
}
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: var(--surface-2);
}
.loading-state, .empty-messages {
  color: var(--text-3);
  font-size: 13px;
  text-align: center;
  margin: auto;
}
.msg-row { display: flex; }
.msg-row--me    { justify-content: flex-end; }
.msg-row--other { justify-content: flex-start; }
.bubble { max-width: 72%; display: flex; flex-direction: column; gap: 3px; }
.msg-row--me .bubble {
  background: var(--accent);
  color: var(--accent-fg);
  border-radius: var(--r) var(--r-sm) var(--r) var(--r);
  padding: 8px 12px;
}
.msg-row--other .bubble {
  background: var(--surface);
  color: var(--text);
  border-radius: var(--r-sm) var(--r) var(--r) var(--r);
  padding: 8px 12px;
  border: 0.5px solid var(--border);
}
.bubble-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10px;
  opacity: .75;
  font-family: var(--font-mono);
  letter-spacing: 0.5px;
}
.msg-row--me .bubble-meta { justify-content: flex-end; }
.bubble-sender { font-weight: 600; }
.bubble-content { font-size: 13px; line-height: 1.5; white-space: pre-wrap; word-break: break-word; }
.composer {
  display: flex;
  gap: 8px;
  padding: 12px 14px;
  border-top: 0.5px solid var(--border);
  background: var(--surface);
  flex-shrink: 0;
}
.composer-input {
  flex: 1;
  padding: 9px 14px;
  border: 0.5px solid var(--border);
  border-radius: var(--r);
  background: var(--surface-2);
  color: var(--text);
  font-family: var(--font-body);
  font-size: 13px;
}
.composer-input:focus { border-color: var(--accent); outline: none; }
.composer-input:disabled { opacity: 0.5; }
.composer-btn {
  padding: 9px 18px;
  border-radius: var(--r);
  background: var(--accent);
  color: var(--accent-fg);
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 500;
  border: none;
  cursor: pointer;
}
.composer-btn:hover:not(:disabled) { background: var(--accent-hover); }
.composer-btn:disabled { opacity: .4; cursor: not-allowed; }
</style>
