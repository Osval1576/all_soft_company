<template>
  <div class="auth-page">
    <div class="auth-inner" v-if="!sent">
      <div class="side">
        <p class="eyebrow">Nueva organización</p>
        <h1 class="lead">
          Registrá<br />
          <span class="lead-accent">tu empresa.</span>
        </h1>
        <p class="note">
          Creamos tu organización y te dejamos como admin. Después invitás al resto del equipo.
        </p>
      </div>

      <form @submit.prevent="onSubmit" class="form" novalidate>
        <label class="field">
          <span class="field-label">Organización</span>
          <input
            v-model="orgName"
            placeholder="nombre de tu empresa"
            autocomplete="organization"
            required
          />
        </label>

        <label class="field">
          <span class="field-label">Nombre</span>
          <input v-model="firstName" placeholder="tu nombre" autocomplete="given-name" required />
        </label>

        <label class="field">
          <span class="field-label">Apellido</span>
          <input v-model="lastName" placeholder="tu apellido" autocomplete="family-name" />
        </label>

        <label class="field">
          <span class="field-label">Email</span>
          <input
            v-model="email"
            type="email"
            placeholder="vos@empresa.com"
            autocomplete="email"
            required
          />
        </label>

        <label class="field">
          <span class="field-label">Contraseña</span>
          <input
            v-model="password"
            type="password"
            placeholder="mínimo 8 caracteres"
            autocomplete="new-password"
            required
          />
        </label>

        <div v-if="error" class="error-msg">{{ error }}</div>

        <button type="submit" :disabled="loading" class="btn-submit">
          <span>{{ loading ? "Creando cuenta..." : "Crear cuenta" }}</span>
          <span v-if="!loading" class="arrow" aria-hidden="true">→</span>
        </button>

        <p class="hint">
          ¿Ya tenés cuenta? <router-link :to="{ name: 'login' }">Iniciá sesión</router-link>.
        </p>
      </form>
    </div>

    <div class="auth-inner sent-inner" v-else>
      <div class="sent-panel">
        <p class="eyebrow">Revisá tu email</p>
        <h1 class="lead">
          Revisá tu email<br />
          <span class="lead-accent">para activar la cuenta.</span>
        </h1>
        <p class="note">
          Te mandamos un link de activación a <strong>{{ email }}</strong>. Si no llega en unos
          minutos, revisá spam o pedí que te lo reenviemos.
        </p>

        <div v-if="resendMsg" class="ok-msg">{{ resendMsg }}</div>
        <div v-if="resendError" class="error-msg">{{ resendError }}</div>

        <button type="button" :disabled="resending" class="btn-submit" @click="onResend">
          <span>{{ resending ? "Reenviando..." : "Reenviar email" }}</span>
        </button>

        <p class="hint">
          <router-link :to="{ name: 'login' }">Volver a iniciar sesión</router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { registerOrg, resendVerification } from "../../api/accounts.api";

const orgName = ref("");
const firstName = ref("");
const lastName = ref("");
const email = ref("");
const password = ref("");

const loading = ref(false);
const error = ref("");
const sent = ref(false);

const resending = ref(false);
const resendMsg = ref("");
const resendError = ref("");

function extractError(e) {
  return (
    e?.response?.data?.detail ||
    Object.values(e?.response?.data || {}).flat()[0] ||
    e.message ||
    "Error al registrar la cuenta"
  );
}

async function onSubmit() {
  if (!orgName.value || !firstName.value || !email.value || !password.value) return;
  loading.value = true;
  error.value = "";
  try {
    await registerOrg({
      org_name: orgName.value,
      first_name: firstName.value,
      last_name: lastName.value,
      email: email.value,
      password: password.value,
    });
    sent.value = true;
  } catch (e) {
    error.value = extractError(e);
  } finally {
    loading.value = false;
  }
}

async function onResend() {
  resending.value = true;
  resendMsg.value = "";
  resendError.value = "";
  try {
    await resendVerification(email.value);
    resendMsg.value = "Listo, te reenviamos el email de activación.";
  } catch (e) {
    resendError.value = extractError(e);
  } finally {
    resending.value = false;
  }
}
</script>

<style scoped>
.auth-page {
  min-height: calc(100vh - 68px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 64px 32px;
  position: relative;
  overflow: hidden;
}
.auth-page::before {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(
    600px circle at 30% 30%,
    var(--accent-glow),
    transparent 60%
  );
  opacity: 0.5;
  pointer-events: none;
}
[data-theme="dark"] .auth-page::before { opacity: 0.7; }

.auth-inner {
  position: relative;
  z-index: 1;
  max-width: 960px;
  width: 100%;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 72px;
  align-items: center;
}
.sent-inner { grid-template-columns: 1fr; justify-items: center; text-align: center; }
.sent-panel { max-width: 480px; }

.eyebrow {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--text-3);
  margin: 0 0 24px;
}

.lead {
  font-family: var(--font-display);
  font-weight: 500;
  font-size: clamp(36px, 5vw, 64px);
  line-height: 1.02;
  letter-spacing: -0.03em;
  margin: 0 0 20px;
  color: var(--text);
}
.lead-accent { color: var(--accent); }
[data-theme="dark"] .lead-accent { color: var(--accent-2); }

.note {
  font-size: 15px;
  color: var(--text-2);
  line-height: 1.6;
  max-width: 380px;
  margin: 0 0 24px;
}
.sent-panel .note { margin: 0 auto 24px; }

.form { display: flex; flex-direction: column; gap: 8px; }

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-bottom: 0.5px solid var(--border);
  padding: 14px 0 10px;
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

.field input {
  background: transparent;
  border: none;
  outline: none;
  padding: 4px 0 6px;
  font-family: var(--font-body);
  font-size: 16px;
  color: var(--text);
}
.field input::placeholder { color: var(--text-3); }

.error-msg {
  margin: 14px 0 0;
  padding: 10px 14px;
  border: 0.5px solid var(--c-urgent, #c33);
  border-radius: 6px;
  background: transparent;
  color: var(--c-urgent, #c33);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 1px;
  text-transform: uppercase;
}

.ok-msg {
  margin: 0 0 20px;
  padding: 10px 14px;
  border: 0.5px solid var(--accent);
  border-radius: 6px;
  background: transparent;
  color: var(--text);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 1px;
  text-transform: uppercase;
}

.btn-submit {
  margin-top: 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background: var(--accent);
  color: var(--accent-fg);
  border: none;
  padding: 14px 22px;
  border-radius: 6px;
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.2px;
  cursor: pointer;
  box-shadow: 0 10px 28px -12px var(--accent-glow);
  transition: transform .12s, box-shadow .15s, opacity .15s;
}
.btn-submit:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 14px 30px -10px var(--accent-glow); }
.btn-submit:disabled { opacity: .55; cursor: not-allowed; }
.btn-submit .arrow { transition: transform .18s; }
.btn-submit:hover:not(:disabled) .arrow { transform: translateX(3px); }

.hint {
  margin: 24px 0 0;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--text-3);
  text-align: center;
}
.hint a { color: var(--accent); text-decoration: none; }
[data-theme="dark"] .hint a { color: var(--accent-2); }
.hint a:hover { text-decoration: underline; text-underline-offset: 3px; }

@media (max-width: 800px) {
  .auth-inner { grid-template-columns: 1fr; gap: 40px; }
  .side { text-align: center; }
  .note { margin-left: auto; margin-right: auto; }
}
</style>
