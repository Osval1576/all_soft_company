<template>
  <div class="panel">
    <header class="header">
      <div class="h-title">{{ title }}</div>
      <div class="h-sub">Chat</div>
    </header>

    <section class="messages" ref="messagesEl">
      <div v-if="loading">Cargando mensajes...</div>

      <div v-for="m in messages" :key="m.id" class="msg">
        <div class="msg-meta">
          <strong>{{ m.sender_username }}</strong>
          <span class="role">({{ m.sender_role }})</span>
          <span class="time">{{ formatTime(m.created_at) }}</span>
        </div>
        <div class="msg-content">{{ m.content }}</div>
      </div>
    </section>

    <footer class="composer">
      <input
        v-model="draft"
        @keydown.enter.prevent="send()"
        placeholder="Escribe un mensaje..."
      />
      <button @click="send" :disabled="!draft.trim()">Enviar</button>
    </footer>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from "vue";
import { getTicketMessages } from "../api/tickets.api";

const props = defineProps({
  ticketId: { type: Number, required: true },
  title: { type: String, default: "" },
});

const messages = ref([]);
const loading = ref(false);
const draft = ref("");
const ws = ref(null);
const messagesEl = ref(null);

function wsUrl(ticketId) {
  return `ws://127.0.0.1:8000/ws/chat/${ticketId}/`;
}

function scrollToBottom() {
  if (!messagesEl.value) return;
  messagesEl.value.scrollTop = messagesEl.value.scrollHeight;
}

function formatTime(iso) {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
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

  ws.value = new WebSocket(wsUrl(props.ticketId));

  ws.value.onmessage = async (evt) => {
    const data = JSON.parse(evt.data);
    messages.value.push(data);
    await nextTick();
    scrollToBottom();
  };

  ws.value.onclose = () => {
    // opcional: reintento
  };
}

function send() {
  const text = draft.value.trim();
  if (!text) return;
  if (!ws.value || ws.value.readyState !== WebSocket.OPEN) return;

  ws.value.send(JSON.stringify({ content: text }));
  draft.value = "";
}

watch(
  () => props.ticketId,
  async () => {
    await loadHistory();
    connectWs();
  },
  { immediate: true }
);

onBeforeUnmount(() => {
  if (ws.value) ws.value.close();
});
</script>

<style scoped>
.panel { display: flex; flex-direction: column; height: 100%; border: 1px solid #eee; border-radius: 8px; overflow: hidden; }
.header { padding: 10px 12px; border-bottom: 1px solid #eee; background: white; }
.h-title { font-weight: 700; }
.h-sub { font-size: 12px; color: #666; margin-top: 2px; }
.messages { flex: 1; overflow: auto; padding: 12px; background: #fafafa; }
.msg { background: white; border: 1px solid #eee; padding: 8px 10px; margin-bottom: 10px; border-radius: 8px; }
.msg-meta { font-size: 12px; color: #444; display: flex; gap: 8px; align-items: center; }
.role { color: #666; }
.time { margin-left: auto; color: #888; }
.msg-content { margin-top: 4px; white-space: pre-wrap; }
.composer { display: flex; gap: 8px; padding: 10px; border-top: 1px solid #eee; background: white; }
.composer input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 8px; }
.composer button { padding: 10px 14px; }
</style>