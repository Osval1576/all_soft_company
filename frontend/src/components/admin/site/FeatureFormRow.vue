<template>
  <div class="row">
    <input v-model="local.icon" placeholder="icon" style="width:90px" />
    <input v-model="local.title_es" placeholder="Título ES" />
    <input v-model="local.title_en" placeholder="Title EN" />
    <input type="checkbox" v-model="local.is_active" title="Activo" />
    <button @click="$emit('save', local)">Guardar</button>
    <button @click="$emit('remove', local.id)" class="del">Borrar</button>
  </div>
</template>

<script setup>
import { reactive, watch } from "vue";
const props = defineProps({ feature: Object });
const local = reactive({ ...props.feature });
watch(() => props.feature, (v) => Object.assign(local, v));
</script>

<style scoped>
.row { display: flex; gap: 6px; align-items: center; width: 100%; }
input[type=text], input:not([type]) { flex: 1; padding: 6px 8px; border: 1px solid var(--border); border-radius: var(--r-sm); background: var(--surface); color: var(--text); font-size: 13px; }
button { padding: 5px 10px; border-radius: var(--r-sm); border: 1px solid var(--border); background: var(--surface); color: var(--text); cursor: pointer; font-size: 12px; }
button.del { color: var(--c-urgent, #c33); }
</style>
