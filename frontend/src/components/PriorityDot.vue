<template>
  <span class="dot" :class="`dot--${priority.toLowerCase()}`" :title="LABELS[priority]"></span>
</template>

<script setup>
defineProps({ priority: { type: String, required: true } })

const LABELS = { LOW: 'Baja', MEDIUM: 'Media', HIGH: 'Alta', URGENT: 'Urgente' }
</script>

<style scoped>
.dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dot--low    { background: var(--c-low); }
.dot--medium { background: var(--c-medium); }
.dot--high   { background: var(--c-high); }
.dot--urgent { background: var(--c-urgent); }
</style>