<template>
  <div class="page">
    <AppTopBar title="Suscripción" />
    <div class="wrap">
      <div v-if="loading" class="state">Cargando…</div>
      <div v-else-if="error" class="state state--error">{{ error }}</div>
      <template v-else>
        <p v-if="billingUnavailable" class="warn-msg">Billing no disponible en este entorno.</p>

        <section class="card">
          <h2 class="card-title">Plan actual</h2>
          <div class="current">
            <div class="current-main">
              <span class="current-plan">{{ sub.plan_name }}</span>
              <span class="badge" :class="`badge--${sub.status}`">{{ STATUS_LABELS[sub.status] || sub.status }}</span>
            </div>
            <p v-if="sub.status === 'trial' && trialDaysLeft !== null" class="current-detail">
              {{ trialDaysLeft > 0 ? `Quedan ${trialDaysLeft} día${trialDaysLeft === 1 ? '' : 's'} de prueba.` : "El período de prueba vence hoy." }}
            </p>
            <p class="current-detail">Uso: {{ sub.agent_count }}/{{ agentLimitLabel }} agentes</p>
            <button
              v-if="sub.plan !== 'free'"
              class="btn btn--ghost"
              :disabled="portalLoading || billingUnavailable"
              @click="onManage"
            >{{ portalLoading ? "Abriendo…" : "Gestionar suscripción" }}</button>
          </div>
        </section>

        <section class="card">
          <h2 class="card-title">Planes disponibles</h2>
          <div class="plans">
            <div
              v-for="p in sortedPlans"
              :key="p.key"
              class="plan"
              :class="{ 'plan--current': p.key === sub.plan }"
            >
              <div class="plan-head">
                <span class="plan-name">{{ p.name }}</span>
                <span v-if="p.key === sub.plan" class="badge badge--current">Tu plan</span>
              </div>
              <p class="plan-limit">{{ p.max_agents == null ? "Agentes ilimitados" : `Hasta ${p.max_agents} agente${p.max_agents === 1 ? '' : 's'}` }}</p>
              <button
                v-if="p.key !== sub.plan && p.key !== 'free'"
                class="btn"
                :disabled="checkingOut === p.key || billingUnavailable"
                @click="onUpgrade(p.key)"
              >{{ checkingOut === p.key ? "Redirigiendo…" : "Mejorar" }}</button>
            </div>
          </div>
        </section>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppTopBar from "../../components/AppTopBar.vue";
import { useNotificationsStore } from "../../stores/notifications.store";
import { getSubscription, startCheckout, openPortal } from "../../api/billing.api";

const STATUS_LABELS = { trial: "Trial", active: "Activa", past_due: "Pago pendiente", canceled: "Cancelada" };

const route = useRoute();
const router = useRouter();
const notif = useNotificationsStore();

const loading = ref(true);
const error = ref("");
const sub = ref(null);
const checkingOut = ref(null);
const portalLoading = ref(false);
const billingUnavailable = ref(false);

const agentLimitLabel = computed(() => (sub.value?.agent_limit == null ? "∞" : sub.value.agent_limit));
const sortedPlans = computed(() => [...(sub.value?.plans || [])].sort((a, b) => a.order - b.order));
const trialDaysLeft = computed(() => {
  if (!sub.value?.trial_ends_at) return null;
  const diffMs = new Date(sub.value.trial_ends_at) - new Date();
  return Math.max(0, Math.ceil(diffMs / 86400000));
});

function extractError(e, fallback) {
  const data = e?.response?.data;
  if (!data) return fallback;
  if (typeof data === "string") return data;
  if (data.detail) return data.detail;
  return fallback;
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    sub.value = await getSubscription();
  } catch (_) {
    error.value = "No se pudo cargar la suscripción.";
  } finally {
    loading.value = false;
  }
}

async function onUpgrade(planKey) {
  checkingOut.value = planKey;
  try {
    const { url } = await startCheckout(planKey);
    window.location.href = url;
  } catch (e) {
    if (e?.response?.status === 503) {
      billingUnavailable.value = true;
      notif.pushToast({ title: "Billing no disponible en este entorno.", tone: "error" });
    } else {
      notif.pushToast({ title: extractError(e, "No se pudo iniciar el pago."), tone: "error" });
    }
  } finally {
    checkingOut.value = null;
  }
}

async function onManage() {
  portalLoading.value = true;
  try {
    const { url } = await openPortal();
    window.location.href = url;
  } catch (e) {
    if (e?.response?.status === 503) {
      billingUnavailable.value = true;
      notif.pushToast({ title: "Billing no disponible en este entorno.", tone: "error" });
    } else {
      notif.pushToast({ title: extractError(e, "No se pudo abrir el portal."), tone: "error" });
    }
  } finally {
    portalLoading.value = false;
  }
}

onMounted(async () => {
  if (route.query.success) {
    notif.pushToast({ title: "¡Suscripción activada!" });
    router.replace({ query: { ...route.query, success: undefined } });
  } else if (route.query.canceled) {
    notif.pushToast({ title: "Pago cancelado." });
    router.replace({ query: { ...route.query, canceled: undefined } });
  }
  await load();
});
</script>

<style scoped>
.wrap { max-width: 720px; margin: 0 auto; padding: 24px 20px; display: flex; flex-direction: column; gap: 20px; }
.state { color: var(--text-3); }
.state--error { color: var(--c-urgent); }
.warn-msg { padding: 9px 12px; border-radius: var(--r-sm); background: var(--c-urgent-bg); color: var(--c-urgent); font-size: 12px; }
.card { background: var(--surface); border: 0.5px solid var(--border); border-radius: var(--r); padding: 18px; }
.card-title { font-family: var(--font-display); font-size: 15px; font-weight: 600; color: var(--text); margin-bottom: 14px; }

.current { display: flex; flex-direction: column; gap: 6px; align-items: flex-start; }
.current-main { display: flex; align-items: center; gap: 10px; }
.current-plan { font-family: var(--font-display); font-size: 18px; font-weight: 600; color: var(--text); }
.current-detail { font-size: 13px; color: var(--text-2); }

.badge { padding: 3px 9px; border-radius: 100px; font-size: 11px; font-weight: 600; font-family: var(--font-mono); letter-spacing: 0.5px; }
.badge--trial { background: var(--surface-2); color: var(--accent); border: 0.5px solid var(--accent); }
.badge--active { background: var(--c-resolved-bg, var(--surface-2)); color: var(--c-resolved); border: 0.5px solid var(--c-resolved); }
.badge--past_due { background: var(--c-urgent-bg); color: var(--c-urgent); border: 0.5px solid var(--c-urgent); }
.badge--canceled { background: var(--surface-2); color: var(--text-3); border: 0.5px solid var(--border); }
.badge--current { background: var(--surface-2); color: var(--accent); border: 0.5px solid var(--accent); }

.plans { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
.plan { border: 0.5px solid var(--border); border-radius: var(--r); padding: 14px; display: flex; flex-direction: column; gap: 8px; }
.plan--current { border-color: var(--accent); }
.plan-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.plan-name { font-family: var(--font-display); font-size: 14px; font-weight: 600; color: var(--text); }
.plan-limit { font-size: 12px; color: var(--text-3); flex: 1; }

.btn { margin-top: 4px; padding: 8px 16px; border-radius: var(--r-sm); background: var(--accent); color: var(--accent-fg); font-size: 13px; font-weight: 600; transition: background .15s, opacity .15s; }
.btn:hover:not(:disabled) { background: var(--accent-hover); }
.btn:disabled { opacity: .5; cursor: not-allowed; }
.btn--ghost { background: var(--surface-2); color: var(--text); border: 0.5px solid var(--border); align-self: flex-start; }
.btn--ghost:hover:not(:disabled) { background: var(--border); }
</style>
