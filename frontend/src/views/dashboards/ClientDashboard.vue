<template>
  <div class="page">
    <AppTopBar title="Mis Tickets" />

    <div class="content">
      <div class="main-area">
        <aside class="ticket-list">
          <div class="list-toolbar">
            <input v-model="search" placeholder="Buscar ticket..." class="search-input" />
            <button @click="openCreateModal" class="btn-new">+ Nuevo</button>
          </div>

          <div v-if="loadingTickets" class="list-state">Cargando...</div>

          <template v-else>
            <div v-if="filtered.length === 0" class="list-state">
              {{ search ? "Sin resultados." : "No tienes tickets." }}
            </div>

            <button
              v-for="t in filtered"
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
              <div class="ticket-date">{{ formatDate(t.created_at) }}</div>
            </button>
          </template>
        </aside>

        <main class="chat-area">
          <div v-if="!selectedTicket" class="empty-chat">
            <div class="empty-icon">&#128172;</div>
            <p>Selecciona un ticket para abrir el chat</p>
          </div>
          <ChatPanel
            v-else
            :ticket-id="selectedTicket.id"
            :title="`${selectedTicket.reference} — ${selectedTicket.titulo}`"
          />
        </main>
      </div>
    </div>

    <Transition name="modal">
      <div v-if="showModal" class="modal-backdrop" @click.self="closeModal">
        <div class="modal">
          <div class="modal-header">
            <span class="modal-title">Nuevo ticket</span>
            <button class="modal-close" @click="closeModal">&#x2715;</button>
          </div>

          <form @submit.prevent="submitTicket" class="modal-form">
            <div class="field">
              <label class="label">Título *</label>
              <input v-model="form.titulo" placeholder="Describe brevemente el problema" class="input" />
            </div>

            <div class="field">
              <label class="label">Descripción *</label>
              <textarea v-model="form.descripcion" placeholder="Explica el problema con más detalle..." class="textarea" rows="4" />
            </div>

            <div class="field">
              <label class="label">Prioridad</label>
              <select v-model="form.prioridad" class="select">
                <option value="LOW">Baja</option>
                <option value="MEDIUM">Media</option>
                <option value="HIGH">Alta</option>
                <option value="URGENT">Urgente</option>
              </select>
            </div>

            <div v-if="formError" class="error-msg">{{ formError }}</div>

            <div class="modal-actions">
              <button type="button" @click="closeModal" class="btn-cancel">Cancelar</button>
              <button type="submit" :disabled="submitting" class="btn-submit">
                {{ submitting ? "Creando..." : "Crear ticket" }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import AppTopBar from "../../components/AppTopBar.vue";
import ChatPanel from "../../components/ChatPanel.vue";
import StatusBadge from "../../components/StatusBadge.vue";
import PriorityDot from "../../components/PriorityDot.vue";
import { listMyTickets, createTicket } from "../../api/tickets.api";

const tickets        = ref([]);
const loadingTickets = ref(false);
const selectedTicket = ref(null);
const search         = ref("");

const showModal  = ref(false);
const submitting = ref(false);
const formError  = ref("");
const form       = ref({ titulo: "", descripcion: "", prioridad: "MEDIUM" });

const filtered = computed(() => {
  const q = search.value.toLowerCase();
  return q
    ? tickets.value.filter(t => t.titulo.toLowerCase().includes(q) || t.reference.toLowerCase().includes(q))
    : tickets.value;
});

function count(status) {
  return tickets.value.filter(t => t.estado === status).length;
}

function formatDate(iso) {
  try {
    return new Date(iso).toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" });
  } catch { return iso; }
}

async function load() {
  loadingTickets.value = true;
  try {
    tickets.value = await listMyTickets();
    if (tickets.value.length && !selectedTicket.value) selectedTicket.value = tickets.value[0];
  } finally {
    loadingTickets.value = false;
  }
}

function openCreateModal() {
  form.value = { titulo: "", descripcion: "", prioridad: "MEDIUM" };
  formError.value = "";
  showModal.value = true;
}

function closeModal() { showModal.value = false; }

async function submitTicket() {
  if (!form.value.titulo.trim() || !form.value.descripcion.trim()) {
    formError.value = "El título y la descripción son obligatorios.";
    return;
  }
  submitting.value = true;
  formError.value  = "";
  try {
    const created = await createTicket(form.value);
    tickets.value.unshift(created);
    selectedTicket.value = created;
    closeModal();
  } catch (e) {
    formError.value = e?.response?.data?.detail || "No se pudo crear el ticket.";
  } finally {
    submitting.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.page { display: flex; flex-direction: column; height: 100%; }
.content {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 16px 20px;
}
.main-area {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 12px;
}
.ticket-list {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}
.list-toolbar {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
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
.btn-new {
  padding: 7px 14px;
  border-radius: var(--r-sm);
  background: var(--accent);
  color: var(--accent-fg);
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  transition: background .15s;
  flex-shrink: 0;
}
.btn-new:hover { background: var(--accent-hover); }
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
  gap: 4px;
  background: transparent;
}
.ticket-item:hover { background: var(--surface-2); }
.ticket-item--active { background: var(--accent-light); }
.ticket-item--active .ticket-ref { color: var(--accent); }
.ticket-item-top {
  display: flex;
  align-items: center;
  gap: 7px;
}
.ticket-ref { font-size: 11px; color: var(--text-2); font-weight: 600; font-family: var(--font-mono); }
.ticket-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding-left: 15px;
  font-family: var(--font-body);
}
.ticket-date { font-size: 11px; color: var(--text-3); padding-left: 15px; font-family: var(--font-mono); letter-spacing: 0.5px; }
.chat-area { min-height: 0; }
.empty-chat {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r);
  box-shadow: var(--shadow-sm);
}
.empty-icon { font-size: 40px; opacity: .3; }
.empty-chat p { color: var(--text-3); font-size: 13px; }
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.4);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  z-index: 100;
  backdrop-filter: blur(2px);
}
.modal {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  width: 100%;
  max-width: 480px;
  box-shadow: var(--shadow-md);
}
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px 14px;
  border-bottom: 1px solid var(--border);
}
.modal-title { font-weight: 600; font-size: 15px; color: var(--text); }
.modal-close {
  width: 28px;
  height: 28px;
  border-radius: var(--r-sm);
  color: var(--text-3);
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all .15s;
}
.modal-close:hover { background: var(--surface-2); color: var(--text); }
.modal-form {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.field { display: flex; flex-direction: column; gap: 6px; }
.label { font-size: 12px; font-weight: 600; color: var(--text-2); letter-spacing: .3px; }
.input, .textarea, .select {
  padding: 9px 12px;
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
  background: var(--surface-2);
  color: var(--text);
  font-size: 13px;
  transition: border-color .15s;
  width: 100%;
}
.input:focus, .textarea:focus, .select:focus {
  border-color: var(--accent);
  outline: none;
}
.input::placeholder, .textarea::placeholder { color: var(--text-3); }
.textarea { resize: vertical; }
.error-msg {
  padding: 9px 12px;
  border-radius: var(--r-sm);
  background: var(--c-urgent-bg);
  color: var(--c-urgent);
  font-size: 12px;
}
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; padding-top: 4px; }
.btn-cancel {
  padding: 8px 16px;
  border-radius: var(--r-sm);
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text-2);
  font-size: 13px;
  font-weight: 500;
  transition: all .15s;
}
.btn-cancel:hover { background: var(--border); }
.btn-submit {
  padding: 8px 20px;
  border-radius: var(--r-sm);
  background: var(--accent);
  color: var(--accent-fg);
  font-size: 13px;
  font-weight: 600;
  transition: background .15s, opacity .15s;
}
.btn-submit:hover:not(:disabled) { background: var(--accent-hover); }
.btn-submit:disabled { opacity: .5; cursor: not-allowed; }
.modal-enter-active, .modal-leave-active { transition: opacity .2s, transform .2s; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .modal, .modal-leave-to .modal { transform: scale(.96); }
</style>