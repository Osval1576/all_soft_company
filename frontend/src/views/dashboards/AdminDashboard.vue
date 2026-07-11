<template>
  <div class="page">
    <AppTopBar title="Administración" />
    <div class="content">
      <div class="stats-row">
        <div class="stat-card"><span class="stat-value">{{ tickets.length }}</span><span class="stat-label">Total tickets</span></div>
        <div class="stat-card stat-card--open"><span class="stat-value">{{ count('OPEN') }}</span><span class="stat-label">Abiertos</span></div>
        <div class="stat-card stat-card--progress"><span class="stat-value">{{ count('IN_PROGRESS') }}</span><span class="stat-label">En proceso</span></div>
        <div class="stat-card stat-card--resolved"><span class="stat-value">{{ count('RESOLVED') }}</span><span class="stat-label">Resueltos</span></div>
        <div class="stat-card stat-card--users"><span class="stat-value">{{ users.length }}</span><span class="stat-label">Usuarios</span></div>
      </div>

      <section style="display:flex; gap:12px; margin-bottom:24px;">
        <router-link to="/admin/sitio/contenido" class="cms-link">Contenido del sitio</router-link>
        <router-link to="/admin/sitio/equipo" class="cms-link">Equipo</router-link>
        <router-link to="/admin/sitio/ubicaciones" class="cms-link">Ubicaciones</router-link>
        <router-link to="/admin/sla" class="cms-link">SLA</router-link>
        <router-link to="/admin/metricas" class="cms-link">Métricas</router-link>
      </section>

      <div class="tabs">
        <button v-for="tab in TABS" :key="tab.id" class="tab-btn" :class="{ 'tab-btn--active': activeTab === tab.id }" @click="activeTab = tab.id">{{ tab.label }}</button>
      </div>

      <div v-if="activeTab === 'tickets'" class="tab-content">
        <div class="toolbar">
          <input v-model="ticketSearch" placeholder="Buscar ticket..." class="search-input" />
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
          <select v-model="tf.asignado.value" class="inline-select">
            <option value="">Asignado: todos</option>
            <option value="none">Sin asignar</option>
            <option v-for="a in agents" :key="a.id" :value="String(a.id)">{{ a.username }}</option>
          </select>
          <button @click="loadAll" class="btn-refresh">&#8635; Actualizar</button>
        </div>
        <div v-if="loading" class="loading-state">Cargando...</div>
        <div v-else class="data-table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th class="th-sort" @click="tf.toggleSort('reference')">Referencia <span class="sort-ind">{{ sortInd('reference') }}</span></th>
                <th>Título</th>
                <th class="th-sort" @click="tf.toggleSort('estado')">Estado <span class="sort-ind">{{ sortInd('estado') }}</span></th>
                <th class="th-sort" @click="tf.toggleSort('prioridad')">Prioridad <span class="sort-ind">{{ sortInd('prioridad') }}</span></th>
                <th>Creado por</th>
                <th>Asignado a</th>
                <th class="th-sort" @click="tf.toggleSort('created_at')">Fecha <span class="sort-ind">{{ sortInd('created_at') }}</span></th>
                <th>SLA</th>
                <th>CSAT</th>
                <th>Asignar agente</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="tf.result.length === 0"><td colspan="10" class="empty-cell">Sin resultados.</td></tr>
              <tr v-for="t in tf.result" :key="t.id">
                <td><span class="mono">{{ t.reference }}</span></td>
                <td class="td-title">{{ t.titulo }}</td>
                <td>
                  <select :value="t.estado" @change="patchTicket(t, { estado: $event.target.value })" class="inline-select">
                    <option value="OPEN">Abierto</option>
                    <option value="IN_PROGRESS">En proceso</option>
                    <option value="RESOLVED">Resuelto</option>
                    <option value="CLOSED">Cerrado</option>
                  </select>
                </td>
                <td><div class="priority-cell"><PriorityDot :priority="t.prioridad" /><span>{{ PRIORITY_LABELS[t.prioridad] }}</span></div></td>
                <td>{{ userName(t.creado_por) }}</td>
                <td>{{ t.asignado_a ? userName(t.asignado_a) : '—' }}</td>
                <td class="mono">{{ formatDate(t.created_at) }}</td>
                <td><SlaBadge :sla="t.sla" /></td>
                <td><CsatDisplay v-if="t.csat" :csat="t.csat" /><span v-else class="mono">—</span></td>
                <td>
                  <select :value="t.asignado_a ?? ''" @change="patchTicket(t, { asignado_a: $event.target.value || null })" class="inline-select">
                    <option value="">Sin asignar</option>
                    <option v-for="a in agents" :key="a.id" :value="a.id">{{ a.username }}</option>
                  </select>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="activeTab === 'users'" class="tab-content">
        <div class="toolbar">
          <input v-model="userSearch" placeholder="Buscar usuario..." class="search-input" />
          <button @click="openUserModal" class="btn-new">+ Nuevo usuario</button>
        </div>
        <div v-if="loading" class="loading-state">Cargando...</div>
        <div v-else class="data-table-wrap">
          <table class="data-table">
            <thead>
              <tr><th>Usuario</th><th>Email</th><th>Nombre</th><th>Rol</th><th>Activo</th><th></th></tr>
            </thead>
            <tbody>
              <tr v-if="filteredUsers.length === 0"><td colspan="6" class="empty-cell">Sin resultados.</td></tr>
              <tr v-for="u in filteredUsers" :key="u.id">
                <td><strong>{{ u.username }}</strong></td>
                <td>{{ u.email || '—' }}</td>
                <td>{{ [u.first_name, u.last_name].filter(Boolean).join(' ') || '—' }}</td>
                <td><span class="role-badge" :class="`role-badge--${u.role?.toLowerCase()}`">{{ ROLE_LABELS[u.role] || u.role }}</span></td>
                <td><span class="active-dot" :class="u.is_active ? 'active-dot--on' : 'active-dot--off'"></span></td>
                <td><button @click="confirmDelete(u)" class="btn-delete">Eliminar</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <Transition name="modal">
      <div v-if="showUserModal" class="modal-backdrop" @click.self="closeUserModal">
        <div class="modal">
          <div class="modal-header">
            <span class="modal-title">Nuevo usuario</span>
            <button class="modal-close" @click="closeUserModal">&#x2715;</button>
          </div>
          <form @submit.prevent="submitUser" class="modal-form">
            <div class="form-row">
              <div class="field"><label class="label">Usuario *</label><input v-model="uForm.username" class="input" placeholder="nombre_usuario" /></div>
              <div class="field"><label class="label">Contraseña *</label><input v-model="uForm.password" type="password" class="input" placeholder="••••••••" /></div>
            </div>
            <div class="form-row">
              <div class="field"><label class="label">Nombre</label><input v-model="uForm.first_name" class="input" placeholder="Nombre" /></div>
              <div class="field"><label class="label">Apellido</label><input v-model="uForm.last_name" class="input" placeholder="Apellido" /></div>
            </div>
            <div class="field"><label class="label">Email</label><input v-model="uForm.email" type="email" class="input" placeholder="usuario@ejemplo.com" /></div>
            <div class="field">
              <label class="label">Rol</label>
              <select v-model="uForm.role" class="select">
                <option value="CUSTOMER">Cliente</option>
                <option value="AGENT">Técnico (Agente)</option>
              </select>
            </div>
            <div v-if="userFormError" class="error-msg">{{ userFormError }}</div>
            <div class="modal-actions">
              <button type="button" @click="closeUserModal" class="btn-cancel">Cancelar</button>
              <button type="submit" :disabled="submittingUser" class="btn-submit">{{ submittingUser ? 'Creando...' : 'Crear usuario' }}</button>
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
import PriorityDot from "../../components/PriorityDot.vue";
import SlaBadge from "../../components/tickets/SlaBadge.vue";
import CsatDisplay from "../../components/tickets/CsatDisplay.vue";
import { listMyTickets, updateTicket, listUsers, createUser, deleteUser } from "../../api/tickets.api";
import { useTicketFilters } from "../../composables/useTicketFilters.js";
import { useNotificationsStore } from "../../stores/notifications.store";

const notif = useNotificationsStore();

const TABS = [{ id: "tickets", label: "Tickets" }, { id: "users", label: "Usuarios" }];
const PRIORITY_LABELS = { LOW: "Baja", MEDIUM: "Media", HIGH: "Alta", URGENT: "Urgente" };
const ROLE_LABELS = { CUSTOMER: "Cliente", AGENT: "Técnico", ADMIN: "Admin" };

const activeTab = ref("tickets");
const loading = ref(false);
const tickets = ref([]);
const users = ref([]);
const ticketSearch = ref("");
const userSearch = ref("");
const showUserModal = ref(false);
const submittingUser = ref(false);
const userFormError = ref("");
const uForm = ref({ username: "", password: "", first_name: "", last_name: "", email: "", role: "CUSTOMER" });

const agents = computed(() => users.value.filter(u => u.role === "AGENT" || u.is_staff));

const searchedTickets = computed(() => {
  const q = ticketSearch.value.toLowerCase();
  return q
    ? tickets.value.filter(
        (t) => t.titulo.toLowerCase().includes(q) || t.reference.toLowerCase().includes(q)
      )
    : tickets.value;
});

const tf = useTicketFilters(searchedTickets);

const filteredUsers = computed(() => {
  const q = userSearch.value.toLowerCase();
  return q ? users.value.filter(u => u.username.toLowerCase().includes(q) || (u.email || "").toLowerCase().includes(q)) : users.value;
});
const userMap = computed(() => Object.fromEntries(users.value.map(u => [u.id, u])));

function count(status) { return tickets.value.filter(t => t.estado === status).length; }
function userName(id) { return userMap.value[id]?.username ?? `#${id}`; }

function sortInd(key) {
  if (tf.sortKey.value !== key) return "";
  return tf.sortDir.value === "asc" ? "▲" : "▼";
}
function formatDate(iso) {
  try { return new Date(iso).toLocaleDateString("es-MX", { day: "2-digit", month: "2-digit", year: "2-digit" }); }
  catch { return ""; }
}

async function loadAll() {
  loading.value = true;
  try { [tickets.value, users.value] = await Promise.all([listMyTickets(), listUsers()]); }
  finally { loading.value = false; }
}

async function patchTicket(ticket, data) {
  try {
    const updated = await updateTicket(ticket.id, data);
    const idx = tickets.value.findIndex(t => t.id === updated.id);
    if (idx !== -1) tickets.value[idx] = updated;
  } catch (e) { console.error("Error al actualizar ticket:", e); }
}

function openUserModal() { uForm.value = { username: "", password: "", first_name: "", last_name: "", email: "", role: "CUSTOMER" }; userFormError.value = ""; showUserModal.value = true; }
function closeUserModal() { showUserModal.value = false; }

async function submitUser() {
  if (!uForm.value.username.trim() || !uForm.value.password.trim()) { userFormError.value = "El usuario y la contraseña son obligatorios."; return; }
  submittingUser.value = true; userFormError.value = "";
  try {
    const created = await createUser({ ...uForm.value, is_staff: uForm.value.role === "AGENT" });
    users.value.push(created);
    closeUserModal();
  } catch (e) {
    const data = e?.response?.data;
    userFormError.value = data ? Object.entries(data).map(([k, v]) => `${k}: ${[v].flat()[0]}`).join(" · ") : "No se pudo crear el usuario.";
  } finally { submittingUser.value = false; }
}

async function confirmDelete(u) {
  if (!confirm(`¿Eliminar al usuario "${u.username}"? Esta acción no se puede deshacer.`)) return;
  try { await deleteUser(u.id); users.value = users.value.filter(x => x.id !== u.id); }
  catch (e) { notif.pushToast({ title: "No se pudo eliminar el usuario.", tone: "error" }); }
}

onMounted(loadAll);
</script>

<style scoped>
.page { display: flex; flex-direction: column; height: 100%; }
.cms-link { padding: 8px 14px; border: 0.5px solid var(--border); border-radius: var(--r); color: var(--text); text-decoration: none; font-size: 13px; font-weight: 600; }
.cms-link:hover { background: var(--surface-2); }
.content { flex: 1; min-height: 0; display: flex; flex-direction: column; padding: 16px 20px; gap: 16px; overflow-y: auto; }
.stats-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; flex-shrink: 0; }
.stat-card { background: var(--surface); border: 0.5px solid var(--border); border-radius: var(--r); padding: 14px 18px; display: flex; flex-direction: column; gap: 4px; }
.stat-card--open { border-left: 3px solid var(--c-open); }
.stat-card--progress { border-left: 3px solid var(--c-progress); }
.stat-card--resolved { border-left: 3px solid var(--c-resolved); }
.stat-card--users { border-left: 3px solid var(--accent); }
.stat-value { font-size: 24px; font-weight: 500; color: var(--text); line-height: 1.1; font-family: var(--font-display); letter-spacing: -0.02em; }
.stat-label { font-family: var(--font-mono); font-size: 10px; letter-spacing: 1.5px; text-transform: uppercase; color: var(--text-3); font-weight: 400; }
.tabs { display: flex; gap: 4px; border-bottom: 0.5px solid var(--border); flex-shrink: 0; }
.tab-btn { padding: 8px 18px; border-radius: var(--r-sm) var(--r-sm) 0 0; font-size: 13px; font-weight: 500; color: var(--text-2); border-color: transparent; border-bottom: none; transition: all .15s; margin-bottom: -1px; }
.tab-btn:hover { color: var(--text); background: var(--surface-2); }
.tab-btn--active { background: transparent; color: var(--accent); border-bottom: 2px solid var(--accent); font-weight: 600; }
.tab-content { background: var(--surface); border: 0.5px solid var(--border); border-radius: 0 var(--r) var(--r) var(--r); display: flex; flex-direction: column; overflow: hidden; }
.toolbar { display: flex; gap: 8px; padding: 12px; border-bottom: 0.5px solid var(--border); flex-shrink: 0; }
.search-input { flex: 1; padding: 7px 10px; border: 0.5px solid var(--border); border-radius: var(--r-sm); background: var(--surface-2); color: var(--text); font-size: 13px; transition: border-color .15s; }
.search-input:focus { border-color: var(--accent); outline: none; }
.search-input::placeholder { color: var(--text-3); }
.btn-refresh { padding: 7px 14px; border-radius: var(--r-sm); background: var(--surface-2); border: 0.5px solid var(--border); color: var(--text-2); font-size: 13px; font-weight: 500; transition: all .15s; white-space: nowrap; }
.btn-refresh:hover { background: var(--border); color: var(--text); }
.btn-new { padding: 7px 14px; border-radius: var(--r-sm); background: var(--accent); color: var(--accent-fg); font-size: 13px; font-weight: 600; transition: background .15s; white-space: nowrap; }
.btn-new:hover { background: var(--accent-hover); }
.loading-state { color: var(--text-3); font-size: 13px; text-align: center; padding: 32px; }
.data-table-wrap { overflow-x: auto; flex: 1; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { text-align: left; padding: 10px 14px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1.2px; color: var(--text-2); border-bottom: 0.5px solid var(--border); background: var(--surface-2); white-space: nowrap; font-family: var(--font-mono); }
.data-table td { padding: 10px 14px; border-bottom: 0.5px solid var(--border); color: var(--text); vertical-align: middle; font-family: var(--font-body); }
.data-table tr:last-child td { border-bottom: none; }
.data-table tr:hover td { background: var(--surface-2); }
.mono { font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.5px; color: var(--text-2); }
.th-sort { cursor: pointer; user-select: none; }
.th-sort:hover { color: var(--text); }
.sort-ind { font-size: 9px; color: var(--accent); }
.td-title { max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.inline-select { padding: 4px 8px; border: 0.5px solid var(--border); border-radius: var(--r-sm); background: var(--surface-2); color: var(--text); font-size: 12px; cursor: pointer; transition: border-color .15s; }
.inline-select:focus { border-color: var(--accent); outline: none; }
.priority-cell { display: flex; align-items: center; gap: 6px; }
.role-badge { display: inline-block; padding: 2px 8px; border-radius: 100px; font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: .3px; }
.role-badge--customer { background: var(--surface-2); color: var(--text-2); }
.role-badge--agent { background: var(--c-progress-bg); color: var(--c-progress); }
.role-badge--admin { background: var(--accent-light); color: var(--accent); }
.active-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; }
.active-dot--on { background: var(--c-resolved); }
.active-dot--off { background: var(--c-closed); }
.btn-delete { padding: 4px 10px; border-radius: var(--r-sm); background: transparent; border: 0.5px solid var(--border); color: var(--text-3); font-size: 12px; transition: all .15s; }
.btn-delete:hover { background: var(--c-urgent-bg); color: var(--c-urgent); border-color: var(--c-urgent); }
.empty-cell { color: var(--text-3); text-align: center; padding: 32px; }
.modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; padding: 20px; z-index: 100; backdrop-filter: blur(2px); }
.modal { background: var(--surface); border: 0.5px solid var(--border); border-radius: var(--r-lg); width: 100%; max-width: 520px; box-shadow: var(--shadow-md); }
.modal-header { display: flex; align-items: center; justify-content: space-between; padding: 18px 20px 14px; border-bottom: 0.5px solid var(--border); }
.modal-title { font-weight: 600; font-size: 15px; color: var(--text); }
.modal-close { width: 28px; height: 28px; border-radius: var(--r-sm); color: var(--text-3); font-size: 14px; display: flex; align-items: center; justify-content: center; transition: all .15s; }
.modal-close:hover { background: var(--surface-2); color: var(--text); }
.modal-form { padding: 20px; display: flex; flex-direction: column; gap: 14px; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.label { font-size: 12px; font-weight: 600; color: var(--text-2); letter-spacing: .3px; }
.input, .select { padding: 9px 12px; border: 0.5px solid var(--border); border-radius: var(--r-sm); background: var(--surface-2); color: var(--text); font-size: 13px; transition: border-color .15s; width: 100%; }
.input:focus, .select:focus { border-color: var(--accent); outline: none; }
.input::placeholder { color: var(--text-3); }
.error-msg { padding: 9px 12px; border-radius: var(--r-sm); background: var(--c-urgent-bg); color: var(--c-urgent); font-size: 12px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; padding-top: 4px; }
.btn-cancel { padding: 8px 16px; border-radius: var(--r-sm); background: var(--surface-2); border: 0.5px solid var(--border); color: var(--text-2); font-size: 13px; font-weight: 500; transition: all .15s; }
.btn-cancel:hover { background: var(--border); }
.btn-submit { padding: 8px 20px; border-radius: var(--r-sm); background: var(--accent); color: var(--accent-fg); font-size: 13px; font-weight: 600; transition: background .15s, opacity .15s; }
.btn-submit:hover:not(:disabled) { background: var(--accent-hover); }
.btn-submit:disabled { opacity: .5; cursor: not-allowed; }
.modal-enter-active, .modal-leave-active { transition: opacity .2s, transform .2s; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .modal, .modal-leave-to .modal { transform: scale(.96); }
</style>