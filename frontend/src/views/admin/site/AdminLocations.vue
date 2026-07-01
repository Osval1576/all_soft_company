<template>
  <div class="al">
    <header class="top">
      <h1>Ubicaciones</h1>
      <button @click="openNew">+ Agregar ubicación</button>
    </header>

    <DragHandleList :items="items" @reorder="onReorder" v-slot="{ item }">
      <div class="row" @click="openEdit(item)">
        <div class="pin">{{ item.type[0] }}</div>
        <div class="info">
          <p class="name">{{ item.name }}</p>
          <p class="addr">{{ item.address }}</p>
        </div>
        <span :class="['dot', item.is_active ? 'on' : 'off']"></span>
      </div>
    </DragHandleList>

    <LocationFormModal v-if="open" :location="editing" @close="open=false" @saved="onSaved" />
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { landingAdminApi } from "../../../api/landing.api";
import DragHandleList from "../../../components/admin/site/DragHandleList.vue";
import LocationFormModal from "../../../components/admin/site/LocationFormModal.vue";

const items = ref([]);
const open = ref(false);
const editing = ref(null);

async function load() { items.value = await landingAdminApi.listLocations(); }
function openNew() { editing.value = null; open.value = true; }
function openEdit(l) { editing.value = l; open.value = true; }
async function onSaved({ id, formData }) {
  if (id) await landingAdminApi.updateLocation(id, formData);
  else await landingAdminApi.createLocation(formData);
  open.value = false;
  await load();
}
async function onReorder(ids) {
  await landingAdminApi.reorderLocations(ids);
  const map = Object.fromEntries(items.value.map(x => [x.id, x]));
  items.value = ids.map(id => map[id]);
}
onMounted(load);
</script>

<style scoped>
.top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.top h1 { font-size: 24px; margin: 0; }
.top button { background: var(--accent); color: var(--accent-fg); border: none; padding: 8px 16px; border-radius: var(--r); font-weight: 600; cursor: pointer; }
.row { display: flex; align-items: center; gap: 12px; width: 100%; cursor: pointer; }
.pin { width: 32px; height: 32px; border-radius: 50%; background: var(--accent); color: var(--accent-fg); display: grid; place-items: center; font-weight: 700; font-size: 13px; }
.info { flex: 1; }
.info .name { margin: 0; font-weight: 600; font-size: 14px; }
.info .addr { margin: 0; color: var(--text-3); font-size: 12px; }
.dot { width: 8px; height: 8px; border-radius: 50%; }
.dot.on { background: var(--c-success, #2a8); }
.dot.off { background: var(--text-3); }
</style>
