<template>
  <div class="ac">
    <h1>Contenido del sitio</h1>

    <section class="block">
      <header><h2>Hero</h2><button @click="saveHero" :disabled="busy.hero">Guardar</button></header>
      <I18nField label="Título" v-model:es="hero.title_es" v-model:en="hero.title_en" />
      <I18nField label="Subtítulo" type="textarea" v-model:es="hero.subtitle_es" v-model:en="hero.subtitle_en" />
      <I18nField label="CTA primario - etiqueta" v-model:es="hero.primary_cta_label_es" v-model:en="hero.primary_cta_label_en" />
      <label>CTA primario - URL <input v-model="hero.primary_cta_url" /></label>
    </section>

    <section class="block">
      <header><h2>Sobre nosotros</h2><button @click="saveAbout" :disabled="busy.about">Guardar</button></header>
      <I18nField label="Misión" type="textarea" v-model:es="about.mission_es" v-model:en="about.mission_en" />
      <I18nField label="Visión" type="textarea" v-model:es="about.vision_es" v-model:en="about.vision_en" />
    </section>

    <section class="block">
      <header><h2>Site settings</h2><button @click="saveSettings" :disabled="busy.settings">Guardar</button></header>
      <label>Google Maps API key <input v-model="settings.google_maps_api_key" /></label>
      <I18nField label="Pie de página" type="textarea" v-model:es="settings.footer_text_es" v-model:en="settings.footer_text_en" />
    </section>

    <section class="block">
      <header><h2>Funcionalidades (cards del landing)</h2><button @click="addFeature">+ Agregar</button></header>
      <DragHandleList :items="features" @reorder="onReorder" v-slot="{ item }">
        <FeatureFormRow :feature="item" @save="onSaveFeature" @remove="onRemoveFeature" />
      </DragHandleList>
    </section>

    <p v-if="msg" class="toast">{{ msg }}</p>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from "vue";
import { landingAdminApi } from "../../../api/landing.api";
import I18nField from "../../../components/admin/site/I18nField.vue";
import DragHandleList from "../../../components/admin/site/DragHandleList.vue";
import FeatureFormRow from "../../../components/admin/site/FeatureFormRow.vue";

const hero = reactive({});
const about = reactive({});
const settings = reactive({});
const features = ref([]);
const busy = reactive({ hero: false, about: false, settings: false });
const msg = ref("");

function toast(t) { msg.value = t; setTimeout(() => (msg.value = ""), 1800); }

async function load() {
  const [h, a, s, fs] = await Promise.all([
    landingAdminApi.getHero(), landingAdminApi.getAbout(),
    landingAdminApi.getSettings(), landingAdminApi.listFeatures(),
  ]);
  Object.assign(hero, h); Object.assign(about, a); Object.assign(settings, s);
  features.value = fs;
}

async function saveHero() { busy.hero = true; try { await landingAdminApi.putHero(hero); toast("Hero guardado"); } finally { busy.hero = false; } }
async function saveAbout() { busy.about = true; try { await landingAdminApi.putAbout(about); toast("Nosotros guardado"); } finally { busy.about = false; } }
async function saveSettings() {
  busy.settings = true;
  const fd = new FormData();
  Object.entries(settings).forEach(([k, v]) => {
    if (v === null || v === undefined) return;
    if (typeof v === "object") fd.append(k, JSON.stringify(v));
    else fd.append(k, v);
  });
  try { await landingAdminApi.putSettings(fd); toast("Ajustes guardados"); }
  finally { busy.settings = false; }
}

async function addFeature() {
  const f = await landingAdminApi.createFeature({
    icon: "sparkles", title_es: "Nuevo", title_en: "New",
    description_es: "", description_en: "", order: features.value.length, is_active: true,
  });
  features.value.push(f);
}
async function onSaveFeature(f) { await landingAdminApi.updateFeature(f.id, f); toast("Card guardada"); }
async function onRemoveFeature(id) {
  await landingAdminApi.deleteFeature(id);
  features.value = features.value.filter(x => x.id !== id);
}
async function onReorder(ids) {
  await landingAdminApi.reorderFeatures(ids);
  const map = Object.fromEntries(features.value.map(f => [f.id, f]));
  features.value = ids.map(id => map[id]);
}

onMounted(load);
</script>

<style scoped>
.ac { display: flex; flex-direction: column; gap: 28px; max-width: 760px; }
h1 { font-size: 24px; margin: 0; }
.block { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-lg); padding: 20px; display: flex; flex-direction: column; gap: 12px; }
.block header { display: flex; justify-content: space-between; align-items: center; }
.block header h2 { font-size: 16px; margin: 0; }
.block header button { background: var(--accent); color: var(--accent-fg); border: none; padding: 6px 14px; border-radius: var(--r); font-size: 13px; font-weight: 600; cursor: pointer; }
label { display: flex; flex-direction: column; gap: 6px; font-size: 12px; color: var(--text-2); font-weight: 600; }
label input { padding: 8px 10px; border: 1px solid var(--border); border-radius: var(--r); background: var(--surface); color: var(--text); }
.toast { position: fixed; bottom: 24px; right: 24px; background: var(--accent); color: var(--accent-fg); padding: 10px 16px; border-radius: var(--r); }
</style>
