<template>
  <div class="page">
    <AppTopBar title="Configuración de SLA" />
    <div class="wrap">
      <div v-if="loading" class="state">Cargando…</div>
      <template v-else>
        <section class="card">
          <h2 class="card-title">Políticas por prioridad (minutos laborales)</h2>
          <table class="tbl">
            <thead><tr><th>Prioridad</th><th>1ª respuesta</th><th>Resolución</th></tr></thead>
            <tbody>
              <tr v-for="p in policies" :key="p.priority">
                <td>{{ PRIO[p.priority] || p.priority }}</td>
                <td><input type="number" min="1" v-model.number="p.first_response_minutes" class="inp" /></td>
                <td><input type="number" min="1" v-model.number="p.resolution_minutes" class="inp" /></td>
              </tr>
            </tbody>
          </table>
          <button class="btn" @click="savePolicies">Guardar políticas</button>
        </section>

        <section class="card">
          <h2 class="card-title">Ventana laboral</h2>
          <div class="row"><label>Zona horaria</label><input v-model="config.business_timezone" class="inp" /></div>
          <div class="row"><label>Días (ISO 1=Lun..7=Dom)</label><input v-model="config.work_days" class="inp" /></div>
          <div class="row"><label>Inicio</label><input type="time" v-model="config.work_start" class="inp" /></div>
          <div class="row"><label>Fin</label><input type="time" v-model="config.work_end" class="inp" /></div>
          <div class="row"><label>Umbral "en riesgo" (%)</label><input type="number" min="1" max="99" v-model.number="config.at_risk_threshold_pct" class="inp" /></div>
          <div class="row"><label>Intervalo scheduler (min)</label><input type="number" min="1" v-model.number="config.scheduler_interval_minutes" class="inp" /></div>
          <label class="chk"><input type="checkbox" v-model="config.scheduler_enabled" /> Scheduler activo</label>
          <button class="btn" @click="saveConfig">Guardar ventana</button>
        </section>

        <section class="card">
          <h2 class="card-title">Feriados</h2>
          <div class="hol-add">
            <input type="date" v-model="newHol.date" class="inp" />
            <input v-model="newHol.name" placeholder="Nombre" class="inp" />
            <button class="btn" @click="addHoliday">Agregar</button>
          </div>
          <ul class="hol-list">
            <li v-for="h in holidays" :key="h.id">
              <span>{{ h.date }} — {{ h.name || "—" }}</span>
              <button class="btn-x" @click="removeHoliday(h.id)">✕</button>
            </li>
          </ul>
        </section>
        <p v-if="saved" class="saved">Guardado ✓</p>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import AppTopBar from "../../../components/AppTopBar.vue";
import {
  getSlaConfig, updateSlaConfig, getSlaPolicies, updateSlaPolicies,
  getHolidays, createHoliday, deleteHoliday,
} from "../../../api/sla.api";

const PRIO = { LOW: "Baja", MEDIUM: "Media", HIGH: "Alta", URGENT: "Urgente" };
const loading = ref(true);
const saved = ref(false);
const config = ref({});
const policies = ref([]);
const holidays = ref([]);
const newHol = ref({ date: "", name: "" });

function flash() { saved.value = true; setTimeout(() => (saved.value = false), 1500); }

async function savePolicies() { policies.value = await updateSlaPolicies(policies.value); flash(); }
async function saveConfig() { config.value = await updateSlaConfig(config.value); flash(); }
async function addHoliday() {
  if (!newHol.value.date) return;
  await createHoliday({ ...newHol.value });
  holidays.value = await getHolidays();
  newHol.value = { date: "", name: "" };
}
async function removeHoliday(id) { await deleteHoliday(id); holidays.value = holidays.value.filter(h => h.id !== id); }

onMounted(async () => {
  try {
    [config.value, policies.value, holidays.value] = await Promise.all([
      getSlaConfig(), getSlaPolicies(), getHolidays(),
    ]);
  } finally { loading.value = false; }
});
</script>

<style scoped>
.wrap { max-width: 720px; margin: 0 auto; padding: 24px 20px; display: flex; flex-direction: column; gap: 20px; }
.state { color: var(--text-3); }
.card { background: var(--surface); border: 0.5px solid var(--border); border-radius: var(--r); padding: 18px; }
.card-title { font-family: var(--font-display); font-size: 15px; font-weight: 600; color: var(--text); margin-bottom: 14px; }
.tbl { width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 12px; }
.tbl th { text-align: left; padding: 6px 8px; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: var(--text-3); font-family: var(--font-mono); }
.tbl td { padding: 6px 8px; border-top: 0.5px solid var(--border); color: var(--text); }
.row { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 7px 0; }
.row label { font-size: 13px; color: var(--text-2); }
.inp { padding: 6px 10px; border: 0.5px solid var(--border); border-radius: var(--r-sm); background: var(--surface-2); color: var(--text); font-size: 13px; }
.inp:focus { border-color: var(--accent); outline: none; }
.chk { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text-2); padding: 8px 0; }
.btn { margin-top: 10px; padding: 8px 16px; border-radius: var(--r-sm); background: var(--accent); color: var(--accent-fg); font-size: 13px; font-weight: 600; }
.btn:hover { background: var(--accent-hover); }
.hol-add { display: flex; gap: 8px; margin-bottom: 12px; }
.hol-list { display: flex; flex-direction: column; gap: 4px; }
.hol-list li { display: flex; align-items: center; justify-content: space-between; padding: 6px 0; border-bottom: 0.5px solid var(--border); font-size: 13px; color: var(--text); }
.btn-x { color: var(--text-3); font-size: 12px; }
.btn-x:hover { color: var(--c-urgent); }
.saved { color: var(--accent); font-size: 13px; text-align: center; }
</style>
