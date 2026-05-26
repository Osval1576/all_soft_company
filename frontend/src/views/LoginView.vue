<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-brand">
        <div class="brand-mark">AS</div>
        <div class="brand-text">
          <span class="brand-name">AllSafe</span>
          <span class="brand-sub">Portal de soporte</span>
        </div>
      </div>

      <form @submit.prevent="onSubmit" class="login-form">
        <div class="field">
          <label class="label">Usuario</label>
          <input v-model="username" placeholder="nombre de usuario" class="input" autocomplete="username" />
        </div>

        <div class="field">
          <label class="label">Contraseña</label>
          <input v-model="password" type="password" placeholder="••••••••" class="input" autocomplete="current-password" />
        </div>

        <div v-if="error" class="error-msg">{{ error }}</div>

        <button type="submit" :disabled="loading" class="btn-submit">
          {{ loading ? "Iniciando sesión..." : "Iniciar sesión" }}
        </button>
      </form>
    </div>

    <button class="theme-toggle" @click="toggle" :title="isDark ? 'Modo claro' : 'Modo oscuro'">
      <span v-if="isDark">&#9788;</span>
      <span v-else>&#9790;</span>
    </button>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useAuthStore } from "../stores/auth.store";
import { useTheme } from "../composables/useTheme";

const auth     = useAuthStore();
const { isDark, toggle } = useTheme();
const username = ref("");
const password = ref("");
const loading  = ref(false);
const error    = ref("");

async function onSubmit() {
  if (!username.value || !password.value) return;
  loading.value = true;
  error.value   = "";
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
  min-height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg);
  padding: 24px;
  position: relative;
}
.login-card {
  width: 100%;
  max-width: 380px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 36px 32px;
  box-shadow: var(--shadow-md);
}
.login-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 32px;
}
.brand-mark {
  width: 44px;
  height: 44px;
  background: var(--accent);
  color: var(--accent-fg);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: .5px;
  flex-shrink: 0;
}
.brand-text { display: flex; flex-direction: column; gap: 2px; }
.brand-name { font-size: 18px; font-weight: 700; color: var(--text); line-height: 1.2; }
.brand-sub  { font-size: 12px; color: var(--text-3); }
.login-form { display: flex; flex-direction: column; gap: 16px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.label { font-size: 12px; font-weight: 600; color: var(--text-2); letter-spacing: .3px; }
.input {
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: var(--r);
  background: var(--surface-2);
  color: var(--text);
  font-size: 14px;
  transition: border-color .15s, box-shadow .15s;
}
.input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-light);
  outline: none;
}
.input::placeholder { color: var(--text-3); }
.error-msg {
  padding: 10px 14px;
  border-radius: var(--r-sm);
  background: var(--c-urgent-bg);
  color: var(--c-urgent);
  font-size: 13px;
}
.btn-submit {
  padding: 11px;
  border-radius: var(--r);
  background: var(--accent);
  color: var(--accent-fg);
  font-size: 14px;
  font-weight: 600;
  transition: background .15s, opacity .15s;
  margin-top: 4px;
}
.btn-submit:hover:not(:disabled) { background: var(--accent-hover); }
.btn-submit:disabled { opacity: .55; cursor: not-allowed; }
.theme-toggle {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 36px;
  height: 36px;
  border-radius: var(--r-sm);
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-2);
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all .15s;
}
.theme-toggle:hover { background: var(--surface-2); color: var(--text); }
</style>