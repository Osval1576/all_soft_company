<!-- frontend/src/components/metrics/WindowSelector.vue -->
<template>
  <div class="sel">
    <button v-for="w in [7, 30, 90]" :key="w" class="sel-btn"
            :class="{ active: modelValue === w }" @click="$emit('update:modelValue', w)">
      {{ w }}d
    </button>
  </div>
</template>

<script setup>
defineProps({ modelValue: Number });
defineEmits(["update:modelValue"]);
</script>

<style scoped>
.sel { display: inline-flex; border: 0.5px solid var(--border); border-radius: var(--r-sm); overflow: hidden; }
.sel-btn { padding: 6px 14px; font-family: var(--font-mono); font-size: 12px; color: var(--text-2);
           background: var(--surface); border-right: 0.5px solid var(--border); }
.sel-btn:last-child { border-right: none; }
.sel-btn.active { background: var(--accent); color: var(--accent-fg); }
</style>
