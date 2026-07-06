<template>
  <div class="csat-display">
    <span class="csat-display-title">Calificación del cliente</span>
    <div class="csat-display-stars">
      <span
        v-for="n in 5"
        :key="n"
        class="csat-display-star"
        :class="{ 'csat-display-star--filled': n <= csat.score }"
      >★</span>
    </div>
    <p v-if="csat.comment" class="csat-display-comment">“{{ csat.comment }}”</p>
  </div>
</template>

<script setup>
defineProps({ csat: { type: Object, required: true } });
</script>

<style scoped>
.csat-display {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 16px;
  background: var(--surface-2);
  border-bottom: 0.5px solid var(--border);
}
.csat-display-title {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--text-3);
}
.csat-display-stars { display: flex; gap: 2px; }
.csat-display-star { font-size: 16px; line-height: 1; color: var(--text-3); }
.csat-display-star--filled { color: var(--accent); }
.csat-display-comment {
  font-size: 13px;
  color: var(--text-2);
  font-style: italic;
}
</style>
