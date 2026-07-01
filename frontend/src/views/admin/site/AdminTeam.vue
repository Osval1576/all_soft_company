<template>
  <div class="at">
    <header class="top">
      <h1>Equipo</h1>
      <button @click="openNew">+ Agregar miembro</button>
    </header>

    <DragHandleList :items="members" @reorder="onReorder" v-slot="{ item }">
      <div class="row" @click="openEdit(item)">
        <img v-if="item.photo" :src="item.photo" :alt="item.name" />
        <div v-else class="avatar">{{ initials(item.name) }}</div>
        <div class="info">
          <p class="name">{{ item.name }}</p>
          <p class="role">{{ item.role_es }}</p>
        </div>
        <span :class="['dot', item.is_active ? 'on' : 'off']"></span>
      </div>
    </DragHandleList>

    <TeamMemberFormModal v-if="open" :member="editing" @close="open=false" @saved="onSaved" />
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { landingAdminApi } from "../../../api/landing.api";
import DragHandleList from "../../../components/admin/site/DragHandleList.vue";
import TeamMemberFormModal from "../../../components/admin/site/TeamMemberFormModal.vue";

const members = ref([]);
const open = ref(false);
const editing = ref(null);

function initials(name="") {
  return name.split(/\s+/).slice(0,2).map(s=>s[0]||"").join("").toUpperCase();
}

async function load() { members.value = await landingAdminApi.listTeam(); }
function openNew() { editing.value = null; open.value = true; }
function openEdit(m) { editing.value = m; open.value = true; }
async function onSaved({ id, formData }) {
  if (id) await landingAdminApi.updateTeam(id, formData);
  else await landingAdminApi.createTeam(formData);
  open.value = false;
  await load();
}
async function onReorder(ids) {
  await landingAdminApi.reorderTeam(ids);
  const map = Object.fromEntries(members.value.map(m => [m.id, m]));
  members.value = ids.map(id => map[id]);
}

onMounted(load);
</script>

<style scoped>
.top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.top h1 { font-size: 24px; margin: 0; }
.top button { background: var(--accent); color: var(--accent-fg); border: none; padding: 8px 16px; border-radius: var(--r); font-weight: 600; cursor: pointer; }
.row { display: flex; align-items: center; gap: 12px; width: 100%; cursor: pointer; }
.row img, .row .avatar { width: 40px; height: 40px; border-radius: 50%; object-fit: cover; }
.row .avatar { background: var(--surface-2); display: grid; place-items: center; font-weight: 600; font-size: 12px; color: var(--text-2); }
.info { flex: 1; }
.info .name { margin: 0; font-weight: 600; font-size: 14px; }
.info .role { margin: 0; color: var(--text-3); font-size: 12px; }
.dot { width: 8px; height: 8px; border-radius: 50%; }
.dot.on { background: var(--c-success, #2a8); }
.dot.off { background: var(--text-3); }
</style>
