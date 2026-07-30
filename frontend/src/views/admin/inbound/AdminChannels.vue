<template>
  <div class="page">
    <AppTopBar title="Canales" />
    <div class="wrap">
      <header class="head">
        <div>
          <p class="eyebrow">Omnicanal</p>
          <h1 class="title">Canales de entrada</h1>
          <p class="sub">Conectá WhatsApp, email, el widget web o Messenger/Instagram. Cada cuenta enruta los mensajes de ese canal a tu organización.</p>
        </div>
      </header>

      <div v-if="loading" class="state">Cargando…</div>

      <template v-else>
        <!-- Alta -->
        <form class="card add" @submit.prevent="onCreate">
          <div class="add-grid">
            <label class="field">
              <span class="field-label">Canal</span>
              <select v-model="form.channel">
                <option v-for="c in CHANNELS" :key="c.value" :value="c.value">{{ c.label }}</option>
              </select>
            </label>
            <label class="field field--grow">
              <span class="field-label">{{ hint.label }}</span>
              <input v-model="form.external_id" :placeholder="hint.placeholder" required />
            </label>
            <button type="submit" :disabled="creating" class="btn-add">
              {{ creating ? "Agregando…" : "Agregar" }}
            </button>
          </div>
          <p class="add-help">{{ hint.help }}</p>
          <div v-if="error" class="error-msg">{{ error }}</div>
        </form>

        <!-- Lista -->
        <p v-if="accounts.length === 0" class="empty">Todavía no conectaste ningún canal.</p>
        <ul v-else class="list">
          <li v-for="a in accounts" :key="a.id" class="row">
            <span class="row-channel">{{ label(a.channel) }}</span>
            <span class="row-id mono">{{ a.external_id }}</span>
            <label class="switch" :title="a.is_active ? 'Activo' : 'Inactivo'">
              <input type="checkbox" :checked="a.is_active" @change="onToggle(a)" />
              <span class="switch-label">{{ a.is_active ? "Activo" : "Inactivo" }}</span>
            </label>
            <button class="row-del" :class="{ 'row-del--confirm': confirmingId === a.id }" @click.stop="onDelete(a)">
              {{ confirmingId === a.id ? "¿Eliminar?" : "Eliminar" }}
            </button>
          </li>
        </ul>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from "vue";
import AppTopBar from "../../../components/AppTopBar.vue";
import { useNotificationsStore } from "../../../stores/notifications.store";
import {
  listChannelAccounts, createChannelAccount, updateChannelAccount, deleteChannelAccount,
} from "../../../api/inbound.api";

const CHANNELS = [
  { value: "whatsapp", label: "WhatsApp", idLabel: "Phone number ID", placeholder: "p. ej. 123456789012345",
    help: "El phone_number_id de la Cloud API de Meta (no el número visible)." },
  { value: "email", label: "Email", idLabel: "Casilla", placeholder: "soporte@tuempresa.com",
    help: "La dirección de la casilla que recibe los correos de soporte." },
  { value: "widget", label: "Widget web", idLabel: "Clave pública del widget", placeholder: "p. ej. wgt_abc123",
    help: "La clave que usa el snippet embebido en tu web (pública, va en el HTML del cliente)." },
  { value: "messenger", label: "Messenger", idLabel: "Page ID", placeholder: "ID de la página de Facebook",
    help: "El ID de la página de Facebook conectada a Messenger." },
  { value: "instagram", label: "Instagram", idLabel: "Instagram account ID", placeholder: "ID de la cuenta de Instagram",
    help: "El ID de la cuenta profesional de Instagram." },
];
const LABELS = Object.fromEntries(CHANNELS.map(c => [c.value, c.label]));

const notif = useNotificationsStore();
const loading = ref(true);
const creating = ref(false);
const error = ref("");
const accounts = ref([]);
const form = reactive({ channel: "whatsapp", external_id: "" });
const confirmingId = ref(null);
let confirmTimer = null;

const hint = computed(() => {
  const c = CHANNELS.find(x => x.value === form.channel) || CHANNELS[0];
  return { label: c.idLabel, placeholder: c.placeholder, help: c.help };
});

function label(ch) { return LABELS[ch] || ch; }

function extractError(e, fallback) {
  const data = e?.response?.data;
  if (!data) return fallback;
  if (typeof data === "string") return data;
  if (data.detail) return data.detail;
  const first = Object.values(data).flat()[0];
  return first || fallback;
}

function resetConfirm() { clearTimeout(confirmTimer); confirmingId.value = null; }

async function load() {
  loading.value = true;
  try { accounts.value = await listChannelAccounts(); }
  finally { loading.value = false; }
}

async function onCreate() {
  creating.value = true;
  error.value = "";
  try {
    await createChannelAccount({ channel: form.channel, external_id: form.external_id.trim(), is_active: true });
    form.external_id = "";
    await load();
  } catch (e) {
    error.value = extractError(e, "No se pudo agregar el canal. ¿Ese identificador ya está en uso?");
  } finally {
    creating.value = false;
  }
}

async function onToggle(a) {
  try {
    await updateChannelAccount(a.id, { is_active: !a.is_active });
    a.is_active = !a.is_active;
  } catch (_) {
    notif.pushToast({ title: "No se pudo cambiar el estado del canal.", tone: "error" });
  }
}

async function onDelete(a) {
  if (confirmingId.value !== a.id) {
    clearTimeout(confirmTimer);
    confirmingId.value = a.id;
    confirmTimer = setTimeout(resetConfirm, 3000);
    return;
  }
  resetConfirm();
  try {
    await deleteChannelAccount(a.id);
    accounts.value = accounts.value.filter(x => x.id !== a.id);
  } catch (_) {
    notif.pushToast({ title: "No se pudo eliminar el canal.", tone: "error" });
  }
}

onMounted(() => { document.addEventListener("click", resetConfirm); load(); });
onBeforeUnmount(() => { document.removeEventListener("click", resetConfirm); clearTimeout(confirmTimer); });
</script>

<style scoped>
.wrap { max-width: 760px; margin: 0 auto; padding: 24px 20px; display: flex; flex-direction: column; gap: 20px; }
.state, .empty { color: var(--text-3); font-size: 14px; }
.empty { padding: 36px 0; text-align: center; border: 0.5px dashed var(--border); border-radius: var(--r); }

.head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.eyebrow { font-family: var(--font-mono); font-size: 10px; letter-spacing: 2px; text-transform: uppercase; color: var(--text-3); margin: 0 0 6px; }
.title { font-family: var(--font-display); font-size: 22px; font-weight: 600; color: var(--text); margin: 0; }
.sub { font-size: 13px; color: var(--text-3); margin: 6px 0 0; max-width: 60ch; }

.card { background: var(--surface); border: 0.5px solid var(--border); border-radius: var(--r); padding: 18px; }
.add-grid { display: flex; gap: 12px; align-items: flex-end; flex-wrap: wrap; }
.field { display: flex; flex-direction: column; gap: 8px; border-bottom: 0.5px solid var(--border); padding: 8px 0 8px; transition: border-color .15s; }
.field--grow { flex: 1; min-width: 200px; }
.field:focus-within { border-bottom-color: var(--accent); }
.field-label { font-family: var(--font-mono); font-size: 10px; letter-spacing: 1.5px; text-transform: uppercase; color: var(--text-3); }
.field input, .field select { background: transparent; border: none; outline: none; padding: 4px 0 2px; font-family: var(--font-body); font-size: 15px; color: var(--text); }
.field select { cursor: pointer; }
.add-help { font-size: 12px; color: var(--text-3); margin: 12px 0 0; }
.btn-add { padding: 9px 18px; border-radius: var(--r-sm); background: var(--accent); color: var(--accent-fg); font-family: var(--font-display); font-size: 13px; font-weight: 600; transition: background .15s, opacity .15s; }
.btn-add:hover:not(:disabled) { background: var(--accent-hover); }
.btn-add:disabled { opacity: .55; cursor: not-allowed; }

.list { display: flex; flex-direction: column; gap: 8px; }
.row { display: flex; align-items: center; gap: 14px; padding: 12px 14px; background: var(--surface); border: 0.5px solid var(--border); border-radius: var(--r-sm); }
.row-channel { font-size: 14px; font-weight: 600; color: var(--text); min-width: 90px; }
.row-id { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; color: var(--text-2); }
.mono { font-family: var(--font-mono); }
.switch { display: flex; align-items: center; gap: 7px; font-size: 12px; color: var(--text-2); cursor: pointer; white-space: nowrap; }
.switch input { cursor: pointer; }
.row-del { padding: 6px 12px; border-radius: var(--r-sm); background: transparent; border: 0.5px solid var(--border); color: var(--text-3); font-size: 12px; transition: color .15s, border-color .15s; }
.row-del:hover { color: var(--c-urgent); }
.row-del--confirm { color: var(--c-urgent); border-color: var(--c-urgent); font-weight: 600; }

.error-msg { margin: 12px 0 0; padding: 9px 12px; border-radius: var(--r-sm); background: var(--c-urgent-bg); color: var(--c-urgent); font-size: 12px; }
</style>
