<template>
  <div class="page">
    <AppTopBar title="Configuración de IA" />
    <div class="wrap">
      <div v-if="loading" class="state">Cargando…</div>
      <template v-else>
        <section class="card">
          <h2 class="card-title">Asistencia con IA</h2>
          <label class="chk">
            <input type="checkbox" v-model="settings.enabled" />
            IA habilitada para esta organización
          </label>
          <p class="hint">
            Apagá el interruptor para desactivar toda la IA sin cambiar de plan.
            La IA también requiere un plan Pro o Business.
          </p>
        </section>

        <section class="card">
          <h2 class="card-title">Límites de uso</h2>
          <div class="row">
            <label>Acciones de IA por usuario / minuto</label>
            <input type="number" min="0" v-model.number="settings.rate_limit_per_min" class="inp" />
          </div>
          <div class="row">
            <label>Consultas de deflección públicas (widget / WhatsApp) por hora</label>
            <input type="number" min="0" v-model.number="settings.public_rate_limit_per_hour" class="inp" />
          </div>
          <p class="hint">
            El tope público protege el widget y los canales anónimos de picos de
            costo/abuso: superado el límite, la consulta escala a un humano sin
            gastar IA. <strong>0 = sin tope.</strong>
          </p>
        </section>

        <section class="card">
          <h2 class="card-title">Presupuesto mensual</h2>
          <div class="row">
            <label>Tope de gasto de IA por mes (USD)</label>
            <input type="number" min="0" step="0.01" v-model.number="settings.monthly_budget_usd" class="inp" />
          </div>
          <div class="row spend">
            <span>Gasto de este mes</span>
            <strong>${{ cost }}</strong>
          </div>
          <div v-if="budget > 0" class="meter">
            <div class="meter-fill" :class="{ over: pct >= 100 }" :style="{ width: Math.min(pct, 100) + '%' }"></div>
          </div>
          <p class="hint">
            Al alcanzar el tope, la IA de la organización se apaga hasta el mes
            siguiente (el helpdesk sigue funcionando sin IA). <strong>0 = sin tope.</strong>
          </p>
        </section>

        <button class="btn" @click="save">Guardar cambios</button>
        <p v-if="saved" class="saved">Guardado ✓</p>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import AppTopBar from "../../../components/AppTopBar.vue";
import { useNotificationsStore } from "../../../stores/notifications.store";
import { getAiSettings, updateAiSettings } from "../../../api/ai.api";

const notif = useNotificationsStore();
const loading = ref(true);
const saved = ref(false);
const settings = ref({});

const cost = computed(() => Number(settings.value.current_month_cost_usd || 0).toFixed(2));
const budget = computed(() => Number(settings.value.monthly_budget_usd || 0));
const pct = computed(() => (budget.value > 0 ? (Number(cost.value) / budget.value) * 100 : 0));

function flash() { saved.value = true; setTimeout(() => (saved.value = false), 1500); }

async function save() {
  try {
    settings.value = await updateAiSettings({
      enabled: settings.value.enabled,
      rate_limit_per_min: settings.value.rate_limit_per_min,
      public_rate_limit_per_hour: settings.value.public_rate_limit_per_hour,
      monthly_budget_usd: settings.value.monthly_budget_usd,
    });
    flash();
  } catch (_) {
    notif.pushToast({ title: "No se pudo guardar la configuración de IA.", tone: "error" });
  }
}

onMounted(async () => {
  try {
    settings.value = await getAiSettings();
  } finally { loading.value = false; }
});
</script>

<style scoped>
.wrap { max-width: 720px; margin: 0 auto; padding: 24px 20px; display: flex; flex-direction: column; gap: 20px; }
.state { color: var(--text-3); }
.card { background: var(--surface); border: 0.5px solid var(--border); border-radius: var(--r); padding: 18px; }
.card-title { font-family: var(--font-display); font-size: 15px; font-weight: 600; color: var(--text); margin-bottom: 14px; }
.row { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 7px 0; }
.row label { font-size: 13px; color: var(--text-2); }
.inp { padding: 6px 10px; border: 0.5px solid var(--border); border-radius: var(--r-sm); background: var(--surface-2); color: var(--text); font-size: 13px; width: 120px; text-align: right; }
.inp:focus { border-color: var(--accent); outline: none; }
.chk { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text-2); padding: 4px 0; }
.hint { font-size: 12px; color: var(--text-3); margin-top: 8px; line-height: 1.5; }
.spend { border-top: 0.5px solid var(--border); margin-top: 6px; padding-top: 12px; }
.spend span { font-size: 13px; color: var(--text-2); }
.spend strong { font-family: var(--font-mono); font-size: 14px; color: var(--text); }
.meter { height: 6px; background: var(--surface-2); border-radius: 3px; overflow: hidden; margin-top: 10px; }
.meter-fill { height: 100%; background: var(--accent); transition: width 0.3s; }
.meter-fill.over { background: var(--c-urgent); }
.btn { padding: 8px 16px; border-radius: var(--r-sm); background: var(--accent); color: var(--accent-fg); font-size: 13px; font-weight: 600; align-self: flex-start; }
.btn:hover { background: var(--accent-hover); }
.saved { color: var(--accent); font-size: 13px; text-align: center; }
</style>
