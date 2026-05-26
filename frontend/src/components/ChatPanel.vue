<template>
  <div class="panel">
    <header v-if="showHeader" class="panel-header">
      <div class="header-info">
        <span class="header-title">{{ title }}</span>
        <span class="header-sub">Chat en tiempo real</span>
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
        placeholder="Escribe un mensaje..."
        class="composer-input"
      />
      <button @click="send" :disabled="!draft.trim()" class="composer-btn">Enviar</button>
    </footer>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, ref, watch, computed } from "vue";
import { getTicketMessages } from "../api/tickets.api";
import { useAuthStore } from "../stores/auth.store";

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

const messages  = ref([]);
const loading   = ref(false);
const draft     = ref("");
const ws        = ref(null);
const messagesEl = ref(null);

function scrollToBottom() {
  if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight;
}

function formatTime(iso) {
  try {
    return new Date(iso).toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" });
  } catch { return iso; }
}

async function loadHistory() {
  loading.value = true;
  try {
    messages.value = await getTicketMessages(props.ticketId);
    await nextTick();
    scrollToBottom();
  } finally {
    loading.value = false;
  }
}

function connectWs() {
  if (ws.value) ws.value.close();
  ws.value = new WebSocket(`ws://localhost:8000/ws/chat/${props.ticketId}/`);
  ws.value.onmessage = async (evt) => {
    messages.value.push(JSON.parse(evt.data));
    await nextTick();
    scrollToBottom();
  };
}

function send() {
  const text = draft.value.trim();
  if (!text || !ws.value || ws.value.readyState !== WebSocket.OPEN) return;
  ws.value.send(JSON.stringify({ content: text }));
  draft.value = "";
}

watch(() => props.ticketId, async () => {
  await loadHistory();
  connectWs();
}, { immediate: true });

onBeforeUnmount(() => { if (ws.value) ws.value.close(); });
</script>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--surface);
  border-radius: var(--r);
  overflow: hidden;
  box-shadow: var(--shadow);
}
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  gap: 12px;
}
.header-info { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.header-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.header-sub { font-size: 11px; color: var(--text-3); }
.status-select {
  padding: 4px 10px;
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
  background: var(--surface-2);
  color: var(--text);
  font-size: 12px;
  cursor: pointer;
}
.status-select:focus { border-color: var(--accent); outline: none; }
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: var(--surface-2);
}
.loading-state,
.empty-messages {
  color: var(--text-3);
  font-size: 13px;
  text-align: center;
  margin: auto;
}
.msg-row { display: flex; }
.msg-row--me    { justify-content: flex-end; }
.msg-row--other { justify-content: flex-start; }
.bubble {
  max-width: 72%;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
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
  box-shadow: var(--shadow-sm);
}
.bubble-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10px;
  opacity: .75;
}
.msg-row--me .bubble-meta { justify-content: flex-end; }
.bubble-sender { font-weight: 600; }
.bubble-content { font-size: 13px; line-height: 1.5; white-space: pre-wrap; word-break: break-word; }
.composer {
  display: flex;
  gap: 8px;
  padding: 12px 14px;
  border-top: 1px solid var(--border);
  background: var(--surface);
  flex-shrink: 0;
}
.composer-input {
  flex: 1;
  padding: 9px 14px;
  border: 1px solid var(--border);
  border-radius: var(--r);
  background: var(--surface-2);
  color: var(--text);
  font-size: 13px;
  transition: border-color .15s;
}
.composer-input:focus { border-color: var(--accent); outline: none; }
.composer-input::placeholder { color: var(--text-3); }
.composer-btn {
  padding: 9px 18px;
  border-radius: var(--r);
  background: var(--accent);
  color: var(--accent-fg);
  font-size: 13px;
  font-weight: 600;
  transition: background .15s, opacity .15s;
  white-space: nowrap;
}
.composer-btn:hover:not(:disabled) { background: var(--accent-hover); }
.composer-btn:disabled { opacity: .4; cursor: not-allowed; }
</style>