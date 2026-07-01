<template>
  <section id="contacto" ref="root" class="contact">
    <h2 class="title">{{ $t("contact.title") }}</h2>
    <form @submit.prevent="submit" class="form">
      <div class="row">
        <label>
          <span>{{ $t("contact.name") }}</span>
          <input v-model="form.name" required maxlength="100" />
        </label>
        <label>
          <span>{{ $t("contact.email") }}</span>
          <input v-model="form.email" type="email" required />
        </label>
      </div>
      <label>
        <span>{{ $t("contact.subject") }}</span>
        <input v-model="form.subject" required maxlength="200" />
      </label>
      <label>
        <span>{{ $t("contact.message") }}</span>
        <textarea v-model="form.message" required maxlength="5000" rows="5"></textarea>
      </label>
      <input v-model="form.website" tabindex="-1" autocomplete="off" class="hp" aria-hidden="true" />
      <p v-if="success" class="ok">{{ success }}</p>
      <p v-if="error" class="err">{{ error }}</p>
      <button :disabled="sending">{{ sending ? "..." : $t("contact.send") }}</button>
    </form>
  </section>
</template>

<script setup>
import { reactive, ref } from "vue";
import { landingApi } from "../../api/landing.api";
import { useScrollReveal } from "../../composables/useScrollReveal";
import { useI18n } from "vue-i18n";

const { t } = useI18n();
const root = ref(null);
useScrollReveal(() => root.value);

const form = reactive({ name: "", email: "", subject: "", message: "", website: "" });
const sending = ref(false);
const success = ref("");
const error = ref("");

async function submit() {
  sending.value = true; success.value = ""; error.value = "";
  try {
    const r = await landingApi.postContact({ ...form });
    if (r.ticket_reference) {
      success.value = t("contact.success", { ref: r.ticket_reference });
      form.name = form.email = form.subject = form.message = "";
    } else {
      success.value = t("contact.success", { ref: "—" });
    }
  } catch (e) {
    error.value = t("contact.error");
  } finally {
    sending.value = false;
  }
}
</script>

<style scoped>
.contact { padding: 64px 0; }
.title { text-align: center; font-size: 32px; margin: 0 0 28px; }
.form { max-width: 560px; margin: 0 auto; display: flex; flex-direction: column; gap: 14px; }
.row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
label { display: flex; flex-direction: column; gap: 6px; font-size: 12px; color: var(--text-2); font-weight: 600; }
input, textarea { padding: 10px 12px; border: 1px solid var(--border); border-radius: var(--r); background: var(--surface); color: var(--text); font-size: 14px; resize: vertical; }
input:focus, textarea:focus { outline: 2px solid var(--accent); }
.hp { position: absolute; left: -9999px; }
button { background: var(--accent); color: var(--accent-fg); border: none; padding: 12px; border-radius: var(--r); font-weight: 600; font-size: 14px; cursor: pointer; }
button:disabled { opacity: .6; cursor: not-allowed; }
.ok { color: var(--c-success, #2a8); font-size: 13px; }
.err { color: var(--c-urgent, #c33); font-size: 13px; }
</style>
