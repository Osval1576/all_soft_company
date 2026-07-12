<template>
  <div class="page">
    <AppTopBar title="Notificaciones" />
    <div class="wrap">
      <h1 class="title">Preferencias de email</h1>
      <p class="sub">Elegí qué avisos querés recibir por correo. Las notificaciones dentro de la app siempre están activas.</p>

      <div v-if="loading" class="state">Cargando…</div>

      <div v-else class="rows">
        <label v-for="opt in visibleOptions" :key="opt.field" class="row">
          <span class="row-info">
            <span class="row-label">{{ opt.label }}</span>
            <span class="row-desc">{{ opt.desc }}</span>
          </span>
          <input
            type="checkbox"
            :checked="prefs[opt.field]"
            @change="onToggle(opt.field, $event.target.checked)"
          />
        </label>
      </div>

      <p v-if="saved" class="saved">Guardado ✓</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import AppTopBar from "../../components/AppTopBar.vue";
import { useAuthStore } from "../../stores/auth.store";
import { useNotificationsStore } from "../../stores/notifications.store";
import { getNotifPreferences, updateNotifPreferences } from "../../api/notifications.api";

const auth = useAuthStore();
const notif = useNotificationsStore();
const loading = ref(true);
const saved = ref(false);
const prefs = ref({});

const ALL_OPTIONS = [
  { field: "email_on_assigned", label: "Ticket asignado", desc: "Cuando un técnico toma tu ticket.", roles: ["CUSTOMER"] },
  { field: "email_on_new_message", label: "Nuevos mensajes", desc: "Cuando te escriben y no estás conectado.", roles: ["CUSTOMER", "AGENT"] },
  { field: "email_on_status_changed", label: "Cambios de estado", desc: "Cuando tu ticket se resuelve o cierra.", roles: ["CUSTOMER"] },
  { field: "email_on_ticket_created", label: "Tickets nuevos", desc: "Cuando entra un ticket nuevo al sistema.", roles: ["ADMIN"] },
];

const myRole = computed(() => auth.user?.role ?? "CUSTOMER");

const visibleOptions = computed(() =>
  ALL_OPTIONS.filter((o) => o.roles.includes(myRole.value))
);

async function onToggle(field, value) {
  const prev = prefs.value[field];
  prefs.value[field] = value;
  saved.value = false;
  try {
    const updated = await updateNotifPreferences({ [field]: value });
    prefs.value = updated;
    saved.value = true;
    setTimeout(() => (saved.value = false), 1500);
  } catch (_) {
    prefs.value[field] = prev;
    notif.pushToast({ title: "No se pudo guardar la preferencia.", tone: "error" });
  }
}

onMounted(async () => {
  try {
    prefs.value = await getNotifPreferences();
  } catch (_) {
    notif.pushToast({ title: "No se pudieron cargar las preferencias.", tone: "error" });
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.wrap { max-width: 560px; margin: 0 auto; padding: 28px 20px; }
.title { font-family: var(--font-display); font-size: 22px; font-weight: 600; color: var(--text); }
.sub { color: var(--text-2); font-size: 14px; margin: 6px 0 24px; }
.state { color: var(--text-3); }
.rows { display: flex; flex-direction: column; gap: 2px; }
.row {
  display: flex; align-items: center; justify-content: space-between; gap: 16px;
  padding: 14px 4px; border-bottom: 0.5px solid var(--border); cursor: pointer;
}
.row-info { display: flex; flex-direction: column; gap: 2px; }
.row-label { font-size: 14px; font-weight: 500; color: var(--text); }
.row-desc { font-size: 12px; color: var(--text-2); }
.row input { width: 18px; height: 18px; accent-color: var(--accent); }
.saved { margin-top: 16px; color: var(--accent); font-size: 13px; }
</style>
