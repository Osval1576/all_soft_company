<template>
  <div class="page">
    <AppTopBar title="Bandeja de entrada" />

    <div class="workspace">
      <aside class="sidebar">
        <div class="sidebar-toolbar">
          <input v-model="search" placeholder="Buscar..." class="search-input" />
          <button @click="load" :disabled="loadingTickets" class="btn-refresh" title="Actualizar">
            &#8635;
          </button>
        </div>

        <div v-if="loadingTickets" class="list-state">Cargando...</div>

        <template v-else>
          <div v-if="filtered.length === 0" class="list-state">
            {{ search ? "Sin resultados." : "No tienes tickets asignados." }}
          </div>

          <button
            v-for="t in filtered"
            :key="t.id"
            class="ticket-item"
            :class="{ 'ticket-item--active': selectedTicket?.id === t.id }"
            @click="selectedTicket = t"
          >
            <div class="ticket-item-row">
              <PriorityDot :priority="t.prioridad" />
              <span class="ticket-ref">{{ t.reference }}</span>
              <StatusBadge :status="t.estado" />
            </div>
            <div class="ticket-title">{{ t.titulo }}</div>
          </button>
        </template>
      </aside>

      <main class="chat-pane">
        <div v-if="!selectedTicket" class="empty-chat">
          <div class="empty-icon">&#128172;</div>
          <p>Selecciona un ticket para abrir el chat</p>
        </div>

        <template v-else>
          <div class="chat-meta-bar">
            <div class="chat-meta-info">
              <span class="chat-meta-ref">{{ selectedTicket.reference }}</span>
              <span class="chat-meta-title">{{ selectedTicket.titulo }}</span>
            </div>
            <div class="status-update">
              <span class="status-label">Estado:</span>
              <select
                :value="selectedTicket.estado"
                @change="changeStatus($event.target.value)"
                class="status-select"
              >
                <option value="OPEN">Abierto</option>
                <option value="IN_PROGRESS">En proceso</option>
                <option value="RESOLVED">Resuelto</option>
                <option value="CLOSED">Cerrado</option>
              </select>
            </div>
          </div>

          <ChatPanel
            :ticket-id="selectedTicket.id"
            :title="selectedTicket.titulo"
            :show-header="false"
          />
        </template>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import AppTopBar from "../../components/AppTopBar.vue";
import ChatPanel from "../../components/ChatPanel.vue";
import StatusBadge from "../../components/StatusBadge.vue";
import PriorityDot from "../../components/PriorityDot.vue";
import { listMyTickets, updateTicket } from "../../api/tickets.api";

const tickets        = ref([]);
const loadingTickets = ref(false);
const selectedTicket = ref(null);
const search         = ref("");

const filtered = computed(() => {
  const q = search.value.toLowerCase();
  return q
    ? tickets.value.filter(t => t.titulo.toLowerCase().includes(q) || t.reference.toLowerCase().includes(q))
    : tickets.value;
});

async function load() {
  loadingTickets.value = true;
  try {
    tickets.value = await listMyTickets();
    if (tickets.value.length && !selectedTicket.value) selectedTicket.value = tickets.value[0];
  } finally {
    loadingTickets.value = false;
  }
}

async function changeStatus(estado) {
  if (!selectedTicket.value) return;
  try {
    const updated = await updateTicket(selectedTicket.value.id, { estado });
    const idx = tickets.value.findIndex(t => t.id === updated.id);
    if (idx !== -1) tickets.value[idx] = updated;
    selectedTicket.value = updated;
  } catch (e) {
    console.error("Error al actualizar estado:", e);
  }
}

onMounted(load);
</script>

<style scoped>
.page { display: flex; flex-direction: column; height: 100%; }
.workspace {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 300px 1fr;
}
.sidebar {
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  background: var(--surface);
}
.sidebar-toolbar {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--surface);
}
.search-input {
  flex: 1;
  padding: 7px 10px;
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
  background: var(--surface-2);
  color: var(--text);
  font-size: 13px;
  transition: border-color .15s;
}
.search-input:focus { border-color: var(--accent); outline: none; }
.search-input::placeholder { color: var(--text-3); }
.btn-refresh {
  width: 34px;
  height: 34px;
  border-radius: var(--r-sm);
  border: 1px solid var(--border);
  background: var(--surface-2);
  color: var(--text-2);
  font-size: 17px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all .15s;
}
.btn-refresh:hover:not(:disabled) { background: var(--border); color: var(--text); }
.btn-refresh:disabled { opacity: .4; cursor: not-allowed; }
.list-state {
  color: var(--text-3);
  font-size: 13px;
  text-align: center;
  padding: 24px 16px;
}
.ticket-item {
  width: 100%;
  text-align: left;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  transition: background .1s;
  display: flex;
  flex-direction: column;
  gap: 5px;
  background: transparent;
}
.ticket-item:hover { background: var(--surface-2); }
.ticket-item--active { background: var(--accent-light); }
.ticket-item--active .ticket-ref { color: var(--accent); }
.ticket-item-row { display: flex; align-items: center; gap: 7px; }
.ticket-ref { font-size: 11px; color: var(--text-2); font-weight: 600; font-family: monospace; }
.ticket-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding-left: 15px;
}
.chat-pane {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--bg);
}
.empty-chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
}
.empty-icon { font-size: 40px; opacity: .3; }
.empty-chat p { color: var(--text-3); font-size: 13px; }
.chat-meta-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
  flex-shrink: 0;
  gap: 12px;
}
.chat-meta-info { display: flex; align-items: center; gap: 10px; min-width: 0; }
.chat-meta-ref {
  font-size: 11px;
  font-weight: 600;
  font-family: monospace;
  color: var(--text-2);
  white-space: nowrap;
}
.chat-meta-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.status-update { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.status-label { font-size: 12px; color: var(--text-2); }
.status-select {
  padding: 5px 10px;
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
  background: var(--surface-2);
  color: var(--text);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: border-color .15s;
}
.status-select:focus { border-color: var(--accent); outline: none; }
.chat-pane > :deep(.panel) { border-radius: 0; box-shadow: none; flex: 1; height: auto; }
</style>