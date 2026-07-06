<template>
  <div class="csat-prompt">
    <p class="csat-title">¿Cómo calificarías la atención que recibiste?</p>
    <div class="csat-stars">
      <button
        v-for="n in 5"
        :key="n"
        type="button"
        class="csat-star"
        :class="{ 'csat-star--filled': n <= (hoverScore || score) }"
        @mouseenter="hoverScore = n"
        @mouseleave="hoverScore = 0"
        @click="score = n"
        :aria-label="`${n} estrellas`"
      >★</button>
    </div>
    <textarea
      v-model="comment"
      placeholder="Comentario (opcional)"
      class="csat-comment"
      rows="2"
    ></textarea>
    <div v-if="error" class="csat-error">{{ error }}</div>
    <button
      type="button"
      class="csat-submit"
      :disabled="!score || submitting"
      @click="submit"
    >{{ submitting ? "Enviando…" : "Enviar calificación" }}</button>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { submitCsat } from "../../api/csat.api";

const props = defineProps({ ticketId: { type: Number, required: true } });
const emit = defineEmits(["submitted"]);

const score = ref(0);
const hoverScore = ref(0);
const comment = ref("");
const submitting = ref(false);
const error = ref("");

async function submit() {
  if (!score.value) return;
  submitting.value = true;
  error.value = "";
  try {
    const payload = await submitCsat(props.ticketId, { score: score.value, comment: comment.value.trim() });
    emit("submitted", payload);
  } catch (err) {
    error.value = err?.response?.data?.detail || "No se pudo enviar la calificación.";
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.csat-prompt {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px 16px;
  background: var(--accent-light);
  border-bottom: 0.5px solid var(--border);
}
.csat-title { font-size: 13px; font-weight: 500; color: var(--text); }
.csat-stars { display: flex; gap: 4px; }
.csat-star {
  font-size: 22px;
  line-height: 1;
  color: var(--text-3);
  background: transparent;
  cursor: pointer;
  transition: color .1s;
}
.csat-star--filled { color: var(--accent); }
.csat-comment {
  padding: 8px 10px;
  border: 0.5px solid var(--border);
  border-radius: var(--r-sm);
  background: var(--surface);
  color: var(--text);
  font-family: var(--font-body);
  font-size: 13px;
  resize: vertical;
}
.csat-comment:focus { border-color: var(--accent); outline: none; }
.csat-error {
  padding: 6px 10px;
  border-radius: var(--r-sm);
  background: var(--c-urgent-bg);
  color: var(--c-urgent);
  font-size: 12px;
}
.csat-submit {
  align-self: flex-start;
  padding: 7px 16px;
  border-radius: var(--r-sm);
  background: var(--accent);
  color: var(--accent-fg);
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 500;
}
.csat-submit:hover:not(:disabled) { background: var(--accent-hover); }
.csat-submit:disabled { opacity: .4; cursor: not-allowed; }
</style>
