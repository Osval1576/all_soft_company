<template>
  <div class="i18n-field">
    <label>{{ label }}</label>
    <div class="tabs">
      <button :class="{active: tab==='es'}" @click="tab='es'" type="button">ES</button>
      <button :class="{active: tab==='en'}" @click="tab='en'" type="button">EN</button>
    </div>
    <template v-if="type==='textarea'">
      <textarea v-if="tab==='es'" :value="es" @input="$emit('update:es', $event.target.value)" rows="4"></textarea>
      <textarea v-else :value="en" @input="$emit('update:en', $event.target.value)" rows="4"></textarea>
    </template>
    <template v-else>
      <input v-if="tab==='es'" :value="es" @input="$emit('update:es', $event.target.value)" />
      <input v-else :value="en" @input="$emit('update:en', $event.target.value)" />
    </template>
  </div>
</template>

<script setup>
import { ref } from "vue";
defineProps({
  label: String, es: String, en: String,
  type: { type: String, default: "input" },
});
defineEmits(["update:es", "update:en"]);
const tab = ref("es");
</script>

<style scoped>
.i18n-field { display: flex; flex-direction: column; gap: 6px; }
label { font-size: 12px; color: var(--text-2); font-weight: 600; }
.tabs { display: flex; gap: 4px; }
.tabs button { padding: 2px 10px; font-size: 11px; border: 1px solid var(--border); border-radius: var(--r-sm); background: transparent; color: var(--text-3); }
.tabs button.active { background: var(--accent); color: var(--accent-fg); border-color: transparent; }
input, textarea { padding: 8px 10px; border: 1px solid var(--border); border-radius: var(--r); background: var(--surface); color: var(--text); font-size: 14px; }
</style>
