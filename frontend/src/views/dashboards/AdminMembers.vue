<template>
  <div class="page">
    <AppTopBar title="Miembros" />
    <div class="wrap">
      <div v-if="loading" class="state">Cargando…</div>
      <template v-else>
        <section class="card">
          <h2 class="card-title">Miembros</h2>
          <table class="tbl" v-if="members.length">
            <thead>
              <tr><th>Usuario</th><th>Email</th><th>Rol</th><th>Activo</th></tr>
            </thead>
            <tbody>
              <tr v-for="m in members" :key="m.id">
                <td><strong>{{ m.username }}</strong></td>
                <td>{{ m.email || "—" }}</td>
                <td>
                  <select
                    :value="m.role"
                    class="inline-select"
                    :disabled="savingId === m.id"
                    @change="onRoleChange(m, $event.target.value)"
                  >
                    <option value="AGENT">Técnico</option>
                    <option value="CUSTOMER">Cliente</option>
                    <option value="ADMIN">Admin</option>
                  </select>
                </td>
                <td>
                  <button
                    class="btn-toggle"
                    :class="m.is_active ? 'btn-toggle--on' : 'btn-toggle--off'"
                    :disabled="savingId === m.id"
                    @click="onToggleActive(m)"
                  >{{ m.is_active ? "Activo" : "Inactivo" }}</button>
                </td>
              </tr>
            </tbody>
          </table>
          <p v-else class="empty">Todavía no hay miembros.</p>
        </section>

        <section class="card">
          <h2 class="card-title">Invitaciones pendientes</h2>
          <p class="agent-usage">Agentes: {{ sub?.agent_count ?? "—" }}/{{ agentLimitLabel }}</p>
          <p v-if="agentLimitReached" class="warn-msg">
            Llegaste al límite de agentes de tu plan.
            <router-link to="/admin/suscripcion">Mejoralo para sumar más.</router-link>
          </p>
          <form class="inv-add" @submit.prevent="onInvite">
            <input
              v-model="newInv.email"
              type="email"
              required
              placeholder="Email a invitar"
              class="inp inp--grow"
            />
            <select v-model="newInv.role" class="inp">
              <option value="AGENT">Técnico</option>
              <option value="CUSTOMER">Cliente</option>
            </select>
            <button type="submit" class="btn" :disabled="inviting || inviteBlocked">{{ inviting ? "Invitando…" : "Invitar" }}</button>
          </form>
          <p v-if="inviteError" class="error-msg">{{ inviteError }}</p>

          <ul class="inv-list" v-if="invitations.length">
            <li v-for="inv in invitations" :key="inv.id">
              <span>{{ inv.email }} — <span class="mono">{{ ROLE_LABELS[inv.role] || inv.role }}</span></span>
              <button
                class="btn-x"
                :class="{ 'btn-x--confirm': confirmingId === inv.id }"
                @click.stop="onRevokeClick(inv.id)"
              >{{ confirmingId === inv.id ? "¿Seguro?" : "Revocar" }}</button>
            </li>
          </ul>
          <p v-else class="empty">No hay invitaciones pendientes.</p>
        </section>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import AppTopBar from "../../components/AppTopBar.vue";
import { useNotificationsStore } from "../../stores/notifications.store";
import {
  listMembers, updateMember,
  listInvitations, createInvitation, revokeInvitation,
} from "../../api/accounts.api";
import { getSubscription } from "../../api/billing.api";

const ROLE_LABELS = { AGENT: "Técnico", CUSTOMER: "Cliente" };

const notif = useNotificationsStore();
const loading = ref(true);
const members = ref([]);
const invitations = ref([]);
const savingId = ref(null);
const newInv = ref({ email: "", role: "AGENT" });
const inviting = ref(false);
const inviteError = ref("");
const confirmingId = ref(null);
let confirmTimer = null;
const sub = ref(null);

const agentLimitLabel = computed(() => (sub.value?.agent_limit == null ? "∞" : sub.value.agent_limit));
const agentLimitReached = computed(
  () => sub.value?.agent_limit != null && sub.value.agent_count >= sub.value.agent_limit,
);
const inviteBlocked = computed(() => newInv.value.role === "AGENT" && agentLimitReached.value);

function extractError(e, fallback) {
  const data = e?.response?.data;
  if (!data) return fallback;
  if (typeof data === "string") return data;
  if (data.detail) return data.detail;
  const first = Object.values(data).find((v) => v);
  if (Array.isArray(first)) return first[0];
  if (typeof first === "string") return first;
  return fallback;
}

async function onRoleChange(member, newRole) {
  const prev = member.role;
  if (prev === newRole) return;
  member.role = newRole;
  savingId.value = member.id;
  try {
    const updated = await updateMember(member.id, { role: newRole });
    Object.assign(member, updated);
  } catch (e) {
    member.role = prev;
    notif.pushToast({ title: extractError(e, "No se pudo cambiar el rol."), tone: "error" });
  } finally {
    savingId.value = null;
  }
}

async function onToggleActive(member) {
  const prev = member.is_active;
  member.is_active = !prev;
  savingId.value = member.id;
  try {
    const updated = await updateMember(member.id, { is_active: !prev });
    Object.assign(member, updated);
  } catch (e) {
    member.is_active = prev;
    notif.pushToast({ title: extractError(e, "No se pudo cambiar el estado."), tone: "error" });
  } finally {
    savingId.value = null;
  }
}

async function onInvite() {
  if (!newInv.value.email.trim()) return;
  inviting.value = true;
  inviteError.value = "";
  try {
    const created = await createInvitation(newInv.value.email.trim(), newInv.value.role);
    invitations.value.unshift(created);
    newInv.value = { email: "", role: "AGENT" };
  } catch (e) {
    inviteError.value = extractError(e, "No se pudo invitar.");
  } finally {
    inviting.value = false;
  }
}

function resetConfirm() {
  clearTimeout(confirmTimer);
  confirmingId.value = null;
}

function onRevokeClick(id) {
  if (confirmingId.value === id) {
    resetConfirm();
    doRevoke(id);
  } else {
    clearTimeout(confirmTimer);
    confirmingId.value = id;
    confirmTimer = setTimeout(resetConfirm, 3000);
  }
}

async function doRevoke(id) {
  try {
    await revokeInvitation(id);
    invitations.value = invitations.value.filter((i) => i.id !== id);
  } catch (e) {
    notif.pushToast({ title: extractError(e, "No se pudo revocar la invitación."), tone: "error" });
  }
}

onMounted(async () => {
  document.addEventListener("click", resetConfirm);
  try {
    [members.value, invitations.value] = await Promise.all([listMembers(), listInvitations()]);
  } finally {
    loading.value = false;
  }
  try {
    sub.value = await getSubscription();
  } catch (_) {
    // el límite de agentes es informativo; si falla, el form queda habilitado
    // y el backend igual valida al invitar.
  }
});

onBeforeUnmount(() => {
  document.removeEventListener("click", resetConfirm);
  clearTimeout(confirmTimer);
});
</script>

<style scoped>
.wrap { max-width: 720px; margin: 0 auto; padding: 24px 20px; display: flex; flex-direction: column; gap: 20px; }
.state { color: var(--text-3); }
.card { background: var(--surface); border: 0.5px solid var(--border); border-radius: var(--r); padding: 18px; }
.card-title { font-family: var(--font-display); font-size: 15px; font-weight: 600; color: var(--text); margin-bottom: 14px; }
.tbl { width: 100%; border-collapse: collapse; font-size: 13px; }
.tbl th { text-align: left; padding: 6px 8px; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: var(--text-3); font-family: var(--font-mono); }
.tbl td { padding: 6px 8px; border-top: 0.5px solid var(--border); color: var(--text); vertical-align: middle; }
.empty { color: var(--text-3); font-size: 13px; }
.inline-select { padding: 4px 8px; border: 0.5px solid var(--border); border-radius: var(--r-sm); background: var(--surface-2); color: var(--text); font-size: 12px; cursor: pointer; transition: border-color .15s; }
.inline-select:focus { border-color: var(--accent); outline: none; }
.inline-select:disabled { opacity: .5; cursor: not-allowed; }
.btn-toggle { padding: 4px 10px; border-radius: 100px; font-size: 11px; font-weight: 600; border: 0.5px solid var(--border); transition: all .15s; }
.btn-toggle--on { background: var(--c-resolved-bg, var(--surface-2)); color: var(--c-resolved); border-color: var(--c-resolved); }
.btn-toggle--off { background: var(--surface-2); color: var(--text-3); }
.btn-toggle:disabled { opacity: .5; cursor: not-allowed; }
.inv-add { display: flex; gap: 8px; margin-bottom: 10px; }
.inp { padding: 6px 10px; border: 0.5px solid var(--border); border-radius: var(--r-sm); background: var(--surface-2); color: var(--text); font-size: 13px; }
.inp:focus { border-color: var(--accent); outline: none; }
.inp--grow { flex: 1; }
.btn { padding: 8px 16px; border-radius: var(--r-sm); background: var(--accent); color: var(--accent-fg); font-size: 13px; font-weight: 600; transition: background .15s, opacity .15s; }
.btn:hover:not(:disabled) { background: var(--accent-hover); }
.btn:disabled { opacity: .5; cursor: not-allowed; }
.error-msg { padding: 9px 12px; border-radius: var(--r-sm); background: var(--c-urgent-bg); color: var(--c-urgent); font-size: 12px; margin-bottom: 10px; }
.agent-usage { font-size: 13px; color: var(--text-2); margin-bottom: 8px; }
.warn-msg { padding: 9px 12px; border-radius: var(--r-sm); background: var(--c-urgent-bg); color: var(--c-urgent); font-size: 12px; margin-bottom: 10px; }
.warn-msg a { color: inherit; font-weight: 600; text-decoration: underline; }
.inv-list { display: flex; flex-direction: column; gap: 4px; }
.inv-list li { display: flex; align-items: center; justify-content: space-between; padding: 6px 0; border-bottom: 0.5px solid var(--border); font-size: 13px; color: var(--text); }
.mono { font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.5px; color: var(--text-2); }
.btn-x { color: var(--text-3); font-size: 12px; }
.btn-x:hover { color: var(--c-urgent); }
.btn-x--confirm { color: var(--c-urgent); font-weight: 600; font-family: var(--font-mono); font-size: 11px; }
</style>
