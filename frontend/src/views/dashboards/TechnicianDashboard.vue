<template>
  <div class="page">
    <AppTopBar title="Panel del técnico" />

    <div class="tech-nav">
      <router-link to="/tecnico/metricas" class="tech-nav-link">Mis métricas</router-link>
    </div>

    <div class="content">
      <div class="stats-row">
        <div class="stat-card">
          <span class="stat-value">{{ stats.open }}</span>
          <span class="stat-label">Asignados abiertos</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ stats.in_progress }}</span>
          <span class="stat-label">En proceso</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ stats.resolved_today }}</span>
          <span class="stat-label">Resueltos hoy</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ stats.resolved_week }}</span>
          <span class="stat-label">Resueltos esta semana</span>
        </div>
      </div>

      <div class="tabs">
        <button
          v-for="tab in TABS"
          :key="tab.id"
          class="tab-btn"
          :class="{ 'tab-btn--active': activeTab === tab.id }"
          @click="activeTab = tab.id"
        >
          {{ tab.label }}
          <span class="tab-count">{{ tab.id === 'mine' ? mine.length : pool.length }}</span>
        </button>
      </div>

      <div v-if="activeTab === 'mine'" class="main-area">
        <div class="mine-col">
          <div class="mine-controls">
            <select v-model="tf.estado.value" class="inline-select">
              <option value="">Estado: todos</option>
              <option value="OPEN">Abierto</option>
              <option value="IN_PROGRESS">En proceso</option>
              <option value="RESOLVED">Resuelto</option>
              <option value="CLOSED">Cerrado</option>
            </select>
            <select v-model="tf.prioridad.value" class="inline-select">
              <option value="">Prioridad: todas</option>
              <option value="LOW">Baja</option>
              <option value="MEDIUM">Media</option>
              <option value="HIGH">Alta</option>
              <option value="URGENT">Urgente</option>
            </select>
            <select :value="tf.sortKey.value" @change="tf.toggleSort($event.target.value)" class="inline-select">
              <option value="prioridad">Orden: prioridad</option>
              <option value="created_at">Orden: fecha</option>
            </select>
            <button
              type="button"
              class="sort-dir-btn"
              @click="tf.toggleSort(tf.sortKey.value)"
              :aria-label="tf.sortDir.value === 'asc' ? 'Orden ascendente, cambiar a descendente' : 'Orden descendente, cambiar a ascendente'"
              :title="tf.sortDir.value === 'asc' ? 'Ascendente' : 'Descendente'"
            >{{ tf.sortDir.value === 'asc' ? '↑' : '↓' }}</button>
          </div>
          <aside class="ticket-list">
            <div v-if="loading" class="list-state">Cargando...</div>
            <template v-else>
              <div v-if="tf.result.length === 0" class="list-state">No tienes tickets asignados.</div>
              <button
                v-for="t in tf.result"
                :key="t.id"
                class="ticket-item"
                :class="{ 'ticket-item--active': selectedTicket?.id === t.id }"
                @click="selectedTicket = t"
              >
                <div class="ticket-item-top">
                  <PriorityDot :priority="t.prioridad" />
                  <span class="ticket-ref">{{ t.reference }}</span>
                  <StatusBadge :status="t.estado" />
                </div>
                <div class="ticket-title">{{ t.titulo }}</div>
                <SlaBadge :sla="t.sla" compact />
              </button>
            </template>
          </aside>
        </div>

        <main class="chat-area">
          <div v-if="!selectedTicket" class="empty-chat">
            <p>Selecciona un ticket para abrir el chat.</p>
          </div>
          <ChatPanel
            v-else
            :ticket-id="selectedTicket.id"
            :title="`${selectedTicket.reference} — ${selectedTicket.titulo}`"
            :status="selectedTicket.estado"
            :can-update-status="true"
            :csat="selectedTicket.csat"
            :can-rate="selectedTicket.can_rate"
            @update:status="onStatusChange"
            @csat-submitted="onCsatSubmitted"
          />
        </main>
      </div>

      <div v-if="activeTab === 'pool'" class="pool-area">
        <div v-if="loadingPool" class="list-state">Cargando pool...</div>
        <PoolList v-else :tickets="pool" @take="onTake" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import AppTopBar from "../../components/AppTopBar.vue";
import ChatPanel from "../../components/ChatPanel.vue";
import PoolList from "../../components/tickets/PoolList.vue";
import StatusBadge from "../../components/StatusBadge.vue";
import PriorityDot from "../../components/PriorityDot.vue";
import SlaBadge from "../../components/tickets/SlaBadge.vue";
import { listMyTickets, updateTicket, getPool, takeTicket } from "../../api/tickets.api";
import { useTicketFilters } from "../../composables/useTicketFilters.js";
import { useNotificationsStore } from "../../stores/notifications.store";

const notif = useNotificationsStore();

const TABS = [
  { id: "mine", label: "Mis tickets" },
  { id: "pool", label: "Pool disponible" },
];

const activeTab = ref("mine");
const loading = ref(false);
const loadingPool = ref(false);
const mine = ref([]);
const pool = ref([]);
const selectedTicket = ref(null);

const tf = useTicketFilters(mine);

const stats = computed(() => {
  const now = new Date();
  const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
  const isResolved = t => t.estado === "RESOLVED";
  return {
    open: mine.value.filter(t => t.estado === "OPEN").length,
    in_progress: mine.value.filter(t => t.estado === "IN_PROGRESS").length,
    resolved_today: mine.value.filter(t => isResolved(t) && new Date(t.updated_at) >= startOfDay).length,
    resolved_week: mine.value.filter(t => isResolved(t) && new Date(t.updated_at) >= weekAgo).length,
  };
});

async function loadMine() {
  loading.value = true;
  try {
    mine.value = await listMyTickets();
    if (!selectedTicket.value && mine.value.length) selectedTicket.value = mine.value[0];
  } finally { loading.value = false; }
}

async function loadPool() {
  loadingPool.value = true;
  try { pool.value = await getPool(); }
  finally { loadingPool.value = false; }
}

async function onTake(ticket) {
  try {
    const updated = await takeTicket(ticket.id);
    pool.value = pool.value.filter(t => t.id !== ticket.id);
    mine.value.unshift(updated);
    selectedTicket.value = updated;
    activeTab.value = "mine";
  } catch (e) {
    if (e?.response?.status === 409) {
      notif.pushToast({ title: "Otro técnico tomó este ticket.", tone: "error" });
      await loadPool();
    } else {
      notif.pushToast({ title: "No se pudo tomar el ticket.", tone: "error" });
    }
  }
}

async function onStatusChange(newStatus) {
  if (!selectedTicket.value) return;
  try {
    const updated = await updateTicket(selectedTicket.value.id, { estado: newStatus });
    const idx = mine.value.findIndex(t => t.id === updated.id);
    if (idx !== -1) mine.value[idx] = updated;
    selectedTicket.value = updated;
  } catch (e) {
    notif.pushToast({ title: e?.response?.data?.estado?.[0] || "No se pudo cambiar el estado.", tone: "error" });
  }
}

function onCsatSubmitted(payload) {
  if (!selectedTicket.value) return;
  selectedTicket.value.csat = payload;
  selectedTicket.value.can_rate = false;
  const idx = mine.value.findIndex(t => t.id === selectedTicket.value.id);
  if (idx !== -1) {
    mine.value[idx].csat = payload;
    mine.value[idx].can_rate = false;
  }
}

onMounted(async () => {
  await Promise.all([loadMine(), loadPool()]);
});
</script>

<style scoped>
.tech-nav { max-width: 1100px; margin: 0 auto; padding: 12px 20px 0; }
.tech-nav-link { font-family: var(--font-mono); font-size: 12px; color: var(--accent);
                 border: 0.5px solid var(--border); border-radius: var(--r-sm); padding: 6px 12px; }
.tech-nav-link:hover { background: var(--accent-light); }
.page { display: flex; flex-direction: column; height: 100%; }
.content { flex: 1; min-height: 0; display: flex; flex-direction: column; padding: 16px 20px; gap: 16px; overflow: hidden; }

.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; flex-shrink: 0; }
.stat-card {
  background: var(--surface);
  border: 0.5px solid var(--border);
  border-radius: var(--r);
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.stat-value {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 500;
  color: var(--text);
  line-height: 1.05;
  letter-spacing: -0.02em;
}
.stat-label {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--text-3);
}

.tabs { display: flex; gap: 4px; border-bottom: 0.5px solid var(--border); flex-shrink: 0; }
.tab-btn {
  padding: 10px 18px;
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-2);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-bottom: -1px;
}
.tab-btn--active { color: var(--accent); border-bottom-color: var(--accent); }
[data-theme="dark"] .tab-btn--active { color: var(--accent-2); border-bottom-color: var(--accent-2); }
.tab-count {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 1px;
  color: var(--text-3);
  background: var(--surface-2);
  padding: 2px 6px;
  border-radius: 3px;
}

.main-area { flex: 1; min-height: 0; display: grid; grid-template-columns: 320px 1fr; gap: 12px; }
.mine-col { display: flex; flex-direction: column; gap: 8px; min-height: 0; }
.mine-col .ticket-list { flex: 1; }
.mine-controls { display: flex; gap: 6px; flex-shrink: 0; }
.mine-controls .inline-select {
  flex: 1;
  padding: 6px 8px;
  border: 0.5px solid var(--border);
  border-radius: var(--r-sm);
  background: var(--surface-2);
  color: var(--text);
  font-size: 12px;
}
.sort-dir-btn {
  flex-shrink: 0;
  width: 30px;
  padding: 6px 0;
  border: 0.5px solid var(--border);
  border-radius: var(--r-sm);
  background: var(--surface-2);
  color: var(--text-2);
  font-size: 13px;
  cursor: pointer;
}
.sort-dir-btn:hover { background: var(--border); color: var(--text); }
.ticket-list {
  background: var(--surface);
  border: 0.5px solid var(--border);
  border-radius: var(--r);
  overflow-y: auto;
}
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
  border-bottom: 0.5px solid var(--border);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 4px;
  background: transparent;
  border-left: none;
  border-right: none;
  border-top: none;
}
.ticket-item:hover { background: var(--surface-2); }
.ticket-item--active { background: var(--accent-light); }
.ticket-item-top { display: flex; align-items: center; gap: 7px; }
.ticket-ref {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 1px;
  color: var(--text-2);
}
.ticket-title {
  font-family: var(--font-body);
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.chat-area { min-height: 0; }
.empty-chat {
  height: 100%;
  display: grid;
  place-items: center;
  color: var(--text-3);
  font-size: 13px;
  background: var(--surface);
  border: 0.5px solid var(--border);
  border-radius: var(--r);
}

.pool-area { flex: 1; overflow-y: auto; padding-right: 4px; }
</style>
