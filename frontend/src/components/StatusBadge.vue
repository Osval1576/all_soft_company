<template>
  <span class="badge" :class="`badge--${cls}`">{{ label }}</span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ status: { type: String, required: true } })

const LABELS = { OPEN: 'Abierto', IN_PROGRESS: 'En proceso', RESOLVED: 'Resuelto', CLOSED: 'Cerrado' }
const label = computed(() => LABELS[props.status] ?? props.status)
const cls   = computed(() => props.status.toLowerCase().replace('_', '-'))
</script>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 100px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: .4px;
  text-transform: uppercase;
  white-space: nowrap;
}
.badge--open        { background: var(--c-open-bg);     color: var(--c-open); }
.badge--in-progress { background: var(--c-progress-bg); color: var(--c-progress); }
.badge--resolved    { background: var(--c-resolved-bg); color: var(--c-resolved); }
.badge--closed      { background: var(--c-closed-bg);   color: var(--c-closed); }
</style>