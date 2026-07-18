<template>
  <div class="auth-page">
    <div class="auth-inner">
      <div class="panel" v-if="status === 'loading'">
        <p class="eyebrow">Verificando</p>
        <h1 class="lead">Activando<br /><span class="lead-accent">tu cuenta...</span></h1>
        <p class="note">Un segundo, estamos validando el link.</p>
      </div>

      <div class="panel" v-else-if="status === 'success'">
        <p class="eyebrow">Listo</p>
        <h1 class="lead">Cuenta<br /><span class="lead-accent">activada.</span></h1>
        <p class="note">Ya podés iniciar sesión con tu email y contraseña.</p>
        <router-link :to="{ name: 'login' }" class="btn-submit">
          <span>Iniciar sesión</span>
          <span class="arrow" aria-hidden="true">→</span>
        </router-link>
      </div>

      <div class="panel" v-else>
        <p class="eyebrow">No pudimos verificar</p>
        <h1 class="lead">Link inválido<br /><span class="lead-accent">o vencido.</span></h1>
        <p class="note">{{ errorMsg }}</p>

        <label class="field">
          <span class="field-label">Email</span>
          <input
            v-model="email"
            type="email"
            placeholder="vos@empresa.com"
            autocomplete="email"
          />
        </label>

        <div v-if="resendMsg" class="ok-msg">{{ resendMsg }}</div>
        <div v-if="resendError" class="error-msg">{{ resendError }}</div>

        <button type="button" :disabled="resending || !email" class="btn-submit" @click="onResend">
          <span>{{ resending ? "Reenviando..." : "Reenviar email de activación" }}</span>
        </button>

        <p class="hint">
          <router-link :to="{ name: 'login' }">Volver a iniciar sesión</router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useRoute } from "vue-router";
import { verifyEmail, resendVerification } from "../../api/accounts.api";

const route = useRoute();

const status = ref("loading");
const errorMsg = ref("");

const email = ref("");
const resending = ref(false);
const resendMsg = ref("");
const resendError = ref("");

function extractError(e) {
  return (
    e?.response?.data?.detail ||
    Object.values(e?.response?.data || {}).flat()[0] ||
    e.message ||
    "No pudimos verificar el email"
  );
}

onMounted(async () => {
  try {
    await verifyEmail(route.params.token);
    status.value = "success";
  } catch (e) {
    errorMsg.value = extractError(e);
    status.value = "error";
  }
});

async function onResend() {
  if (!email.value) return;
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
  max-width: 560px;
  width: 100%;
  display: flex;
  justify-content: center;
}
.panel { max-width: 460px; text-align: center; }

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
  font-size: clamp(32px, 5vw, 56px);
  line-height: 1.05;
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
  margin: 0 auto 24px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-bottom: 0.5px solid var(--border);
  padding: 14px 0 10px;
  margin-bottom: 16px;
  text-align: left;
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
  margin: 0 0 16px;
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
  margin: 0 0 16px;
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
  margin-top: 4px;
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
  text-decoration: none;
  box-shadow: 0 10px 28px -12px var(--accent-glow);
  transition: transform .12s, box-shadow .15s, opacity .15s;
}
.btn-submit:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 14px 30px -10px var(--accent-glow); }
.btn-submit:disabled { opacity: .55; cursor: not-allowed; }
.btn-submit .arrow { transition: transform .18s; }
.btn-submit:hover:not(:disabled) .arrow { transform: translateX(3px); }

.hint {
  margin: 20px 0 0;
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
</style>
