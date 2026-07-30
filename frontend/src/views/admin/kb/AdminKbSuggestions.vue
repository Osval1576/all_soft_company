<template>
  <div class="page">
    <AppTopBar title="Sugerencias de KB" />
    <div class="wrap">
      <header class="head">
        <div>
          <p class="eyebrow">Base de conocimiento</p>
          <h1 class="title">Sugerencias de KB</h1>
          <p class="sub">Borradores que la IA propone al resolver tickets. Revisá, editá y publicá.</p>
        </div>
        <router-link to="/admin/kb" class="btn-ghost">← Artículos</router-link>
      </header>

      <div v-if="loading" class="state">Cargando…</div>

      <template v-else>
        <p v-if="items.length === 0" class="empty">
          No hay sugerencias pendientes. Se generan solas cuando se resuelven tickets.
        </p>

        <ul v-else class="list">
          <li v-for="s in items" :key="s.id" class="card">
            <div class="meta">
              <span v-if="s.source_ticket_ref" class="badge">{{ s.source_ticket_ref }}</span>
              <span class="date">{{ fmtDate(s.created_at) }}</span>
            </div>

            <label class="field">
              <span class="field-label">Título</span>
              <input v-model="s.title" />
            </label>
            <label class="field">
              <span class="field-label">Contenido</span>
              <textarea v-model="s.body" rows="8"></textarea>
            </label>

            <div class="actions">
              <button class="btn-accept" :disabled="busyId === s.id" @click="onAccept(s)">
                {{ busyId === s.id ? "Publicando…" : "Aceptar y publicar" }}
              </button>
              <button
                class="btn-dismiss"
                :class="{ 'btn-dismiss--confirm': confirmingId === s.id }"
                :disabled="busyId === s.id"
                @click="onDismiss(s)"
              >{{ confirmingId === s.id ? "¿Descartar?" : "Descartar" }}</button>
            </div>
          </li>
        </ul>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from "vue";
import AppTopBar from "../../../components/AppTopBar.vue";
import { useNotificationsStore } from "../../../stores/notifications.store";
import {
  listSuggestions, updateSuggestion, acceptSuggestion, dismissSuggestion,
} from "../../../api/kb.api";

const notif = useNotificationsStore();
const loading = ref(true);
const items = ref([]);
const busyId = ref(null);
const confirmingId = ref(null);
let confirmTimer = null;

function fmtDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("es-AR", { day: "2-digit", month: "short", year: "numeric" });
}

function resetConfirm() {
  clearTimeout(confirmTimer);
  confirmingId.value = null;
}

async function onAccept(s) {
  busyId.value = s.id;
  resetConfirm();
  try {
    // Persistí las ediciones antes de aceptar: el backend publica con lo guardado.
    await updateSuggestion(s.id, { title: s.title, body: s.body });
    await acceptSuggestion(s.id);
    items.value = items.value.filter(x => x.id !== s.id);
    notif.pushToast({ title: "Artículo publicado.", tone: "success" });
  } catch (_) {
    notif.pushToast({ title: "No se pudo publicar la sugerencia.", tone: "error" });
  } finally {
    busyId.value = null;
  }
}

async function onDismiss(s) {
  if (confirmingId.value !== s.id) {
    clearTimeout(confirmTimer);
    confirmingId.value = s.id;
    confirmTimer = setTimeout(resetConfirm, 3000);
    return;
  }
  busyId.value = s.id;
  resetConfirm();
  try {
    await dismissSuggestion(s.id);
    items.value = items.value.filter(x => x.id !== s.id);
  } catch (_) {
    notif.pushToast({ title: "No se pudo descartar la sugerencia.", tone: "error" });
  } finally {
    busyId.value = null;
  }
}

onMounted(async () => {
  document.addEventListener("click", resetConfirm);
  try {
    items.value = await listSuggestions("pending");
  } finally { loading.value = false; }
});

onBeforeUnmount(() => {
  document.removeEventListener("click", resetConfirm);
  clearTimeout(confirmTimer);
});
</script>

<style scoped>
.wrap { max-width: 760px; margin: 0 auto; padding: 24px 20px; display: flex; flex-direction: column; gap: 20px; }
.state, .empty { color: var(--text-3); font-size: 14px; }
.empty { padding: 40px 0; text-align: center; border: 0.5px dashed var(--border); border-radius: var(--r); }

.head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.eyebrow { font-family: var(--font-mono); font-size: 10px; letter-spacing: 2px; text-transform: uppercase; color: var(--text-3); margin: 0 0 6px; }
.title { font-family: var(--font-display); font-size: 22px; font-weight: 600; color: var(--text); margin: 0; }
.sub { font-size: 13px; color: var(--text-3); margin: 6px 0 0; }
.btn-ghost { padding: 8px 14px; border-radius: var(--r-sm); border: 0.5px solid var(--border); color: var(--text-2); font-size: 13px; white-space: nowrap; }
.btn-ghost:hover { background: var(--surface-2); }

.list { display: flex; flex-direction: column; gap: 16px; }
.card { background: var(--surface); border: 0.5px solid var(--border); border-radius: var(--r); padding: 18px; }

.meta { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
.badge { font-family: var(--font-mono); font-size: 10px; letter-spacing: 1px; padding: 2px 7px; border-radius: 4px; background: var(--surface-2); color: var(--text-2); }
.date { font-size: 11px; color: var(--text-3); }

.field { display: flex; flex-direction: column; gap: 8px; border-bottom: 0.5px solid var(--border); padding: 12px 0 10px; transition: border-color .15s; }
.field:focus-within { border-bottom-color: var(--accent); }
.field-label { font-family: var(--font-mono); font-size: 10px; letter-spacing: 1.5px; text-transform: uppercase; color: var(--text-3); }
.field input, .field textarea { background: transparent; border: none; outline: none; padding: 4px 0 2px; font-family: var(--font-body); font-size: 15px; color: var(--text); resize: vertical; }

.actions { display: flex; gap: 10px; margin-top: 16px; }
.btn-accept { padding: 9px 18px; border-radius: var(--r-sm); background: var(--accent); color: var(--accent-fg); font-family: var(--font-display); font-size: 13px; font-weight: 600; transition: background .15s, opacity .15s; }
.btn-accept:hover:not(:disabled) { background: var(--accent-hover); }
.btn-accept:disabled { opacity: .55; cursor: not-allowed; }
.btn-dismiss { padding: 9px 14px; border-radius: var(--r-sm); background: transparent; border: 0.5px solid var(--border); color: var(--text-2); font-size: 13px; transition: background .15s, color .15s; }
.btn-dismiss:hover:not(:disabled) { color: var(--c-urgent); }
.btn-dismiss--confirm { color: var(--c-urgent); border-color: var(--c-urgent); font-weight: 600; }
</style>
