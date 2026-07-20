<template>
  <div class="login-page">
    <div class="login-inner">
      <div class="side">
        <div v-if="brandLogo || brandName !== 'AllSafe'" class="brand-mark">
          <img v-if="brandLogo" :src="brandLogo" :alt="brandName" class="brand-logo" />
          <span class="brand-name">{{ brandName }}</span>
        </div>
        <p class="eyebrow">Acceso privado</p>
        <h1 class="lead">
          Bienvenido<br />
          <span class="lead-accent">de vuelta.</span>
        </h1>
        <p class="note">
          Iniciá sesión y volvemos al mismo tablero donde quedaron las conversaciones.
        </p>
      </div>

      <form @submit.prevent="onSubmit" class="form" novalidate>
        <label class="field">
          <span class="field-label">Usuario</span>
          <input
            v-model="username"
            placeholder="tu nombre de usuario"
            autocomplete="username"
            required
          />
        </label>

        <label class="field">
          <span class="field-label">Contraseña</span>
          <input
            v-model="password"
            type="password"
            placeholder="••••••••"
            autocomplete="current-password"
            required
          />
        </label>

        <div v-if="error" class="error-msg">{{ error }}</div>

        <button type="submit" :disabled="loading" class="btn-submit">
          <span>{{ loading ? "Iniciando sesión..." : "Iniciar sesión" }}</span>
          <span v-if="!loading" class="arrow" aria-hidden="true">→</span>
        </button>

        <p class="hint">
          ¿Nuevo por acá? <router-link :to="{ name: 'registro' }">Registrá tu empresa</router-link>.
        </p>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useAuthStore } from "../stores/auth.store";

defineProps({
  brandName: { type: String, default: "AllSafe" },
  brandLogo: { type: String, default: null },
});

const auth = useAuthStore();
const username = ref("");
const password = ref("");
const loading = ref(false);
const error = ref("");

async function onSubmit() {
  if (!username.value || !password.value) return;
  loading.value = true;
  error.value = "";
  try {
    await auth.login(username.value, password.value);
  } catch (e) {
    error.value =
      e?.response?.data?.detail ||
      Object.values(e?.response?.data || {}).flat()[0] ||
      e.message ||
      "Error al iniciar sesión";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-page {
  min-height: calc(100vh - 68px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 64px 32px;
  position: relative;
  overflow: hidden;
}
.login-page::before {
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
[data-theme="dark"] .login-page::before { opacity: 0.7; }

.login-inner {
  position: relative;
  z-index: 1;
  max-width: 960px;
  width: 100%;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 72px;
  align-items: center;
}

.brand-mark {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 0 20px;
}
.brand-logo {
  width: 28px;
  height: 28px;
  object-fit: contain;
  border-radius: 6px;
}
.brand-name {
  font-family: var(--font-display);
  font-weight: 500;
  font-size: 15px;
  color: var(--text);
}

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
  max-width: 320px;
  margin: 0;
}

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
  .login-inner { grid-template-columns: 1fr; gap: 40px; }
  .side { text-align: center; }
  .note { margin-left: auto; margin-right: auto; }
}
</style>
