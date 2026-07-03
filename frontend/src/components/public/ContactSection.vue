<template>
  <section id="contacto" ref="root" class="contact">
    <div class="contact-inner">
      <p class="eyebrow">{{ $t("nav.contact") }}</p>

      <div class="contact-grid">
        <div class="left">
          <h2 class="lead">
            Contanos<br />qué necesitás<br /><span class="lead-accent">resolver.</span>
          </h2>
          <p class="note">
            Te vamos a responder desde el mismo tablero que ves cuando entrás.
            Vas a recibir un número de referencia.
          </p>
        </div>

        <form @submit.prevent="submit" class="form" novalidate>
          <label class="field">
            <span class="field-label">{{ $t("contact.name") }}</span>
            <input v-model="form.name" required maxlength="100" autocomplete="name" />
          </label>

          <label class="field">
            <span class="field-label">{{ $t("contact.email") }}</span>
            <input v-model="form.email" type="email" required autocomplete="email" />
          </label>

          <label class="field">
            <span class="field-label">{{ $t("contact.subject") }}</span>
            <input v-model="form.subject" required maxlength="200" />
          </label>

          <label class="field field--textarea">
            <span class="field-label">{{ $t("contact.message") }}</span>
            <textarea v-model="form.message" required maxlength="5000" rows="4"></textarea>
          </label>

          <input v-model="form.website" tabindex="-1" autocomplete="off" class="hp" aria-hidden="true" />

          <p v-if="success" class="ok">{{ success }}</p>
          <p v-if="error" class="err">{{ error }}</p>

          <button :disabled="sending" class="submit">
            <span>{{ sending ? $t("loading") : $t("contact.send") }}</span>
            <span v-if="!sending" class="arrow" aria-hidden="true">→</span>
          </button>
        </form>
      </div>
    </div>
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
.contact { border-top: 0.5px solid var(--border); padding: 96px 32px 96px; }
.contact-inner { max-width: 1240px; margin: 0 auto; }

.eyebrow {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--text-3);
  margin: 0 0 40px;
}

.contact-grid {
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: 80px;
  align-items: start;
}

.lead {
  font-family: var(--font-display);
  font-weight: 500;
  font-size: clamp(28px, 4vw, 46px);
  line-height: 1.06;
  letter-spacing: -0.02em;
  margin: 0;
  color: var(--text);
}
.lead-accent { color: var(--accent); }
[data-theme="dark"] .lead-accent { color: var(--accent-2); }

.note {
  margin: 24px 0 0;
  font-size: 14px;
  color: var(--text-2);
  line-height: 1.6;
  max-width: 320px;
}

.form { display: flex; flex-direction: column; gap: 8px; }

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-bottom: 0.5px solid var(--border);
  padding: 12px 0 10px;
  transition: border-color .15s;
}
.field:focus-within { border-bottom-color: var(--accent); }
[data-theme="dark"] .field:focus-within { border-bottom-color: var(--accent-2); }

.field-label {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--text-3);
}

.field input, .field textarea {
  background: transparent;
  border: none;
  outline: none;
  padding: 4px 0 6px;
  font-family: var(--font-body);
  font-size: 15px;
  color: var(--text);
  resize: none;
}
.field input::placeholder, .field textarea::placeholder { color: var(--text-3); }
.field--textarea textarea { min-height: 72px; }

.hp { position: absolute; left: -9999px; }

.ok {
  margin: 12px 0 0;
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 1px;
  color: var(--accent);
}
[data-theme="dark"] .ok { color: var(--accent-2); }
.err {
  margin: 12px 0 0;
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 1px;
  color: var(--c-urgent, #c33);
}

.submit {
  align-self: flex-end;
  margin-top: 20px;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  background: var(--accent);
  color: var(--accent-fg);
  border: none;
  padding: 14px 26px;
  border-radius: 6px;
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.2px;
  cursor: pointer;
  box-shadow: 0 10px 28px -12px var(--accent-glow);
  transition: transform .12s, box-shadow .15s, opacity .15s;
}
.submit:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 14px 30px -10px var(--accent-glow); }
.submit:disabled { opacity: .55; cursor: not-allowed; }
.submit .arrow { transition: transform .18s; }
.submit:hover:not(:disabled) .arrow { transform: translateX(3px); }

@media (max-width: 800px) {
  .contact { padding: 56px 20px; }
  .contact-grid { grid-template-columns: 1fr; gap: 32px; }
  .submit { align-self: stretch; justify-content: center; }
}
</style>
