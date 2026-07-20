<template>
  <div class="auth-page">
    <div class="auth-inner" v-if="status === 'loading'">
      <div class="panel">
        <p class="eyebrow">Invitación</p>
        <h1 class="lead">Cargando<br /><span class="lead-accent">la invitación...</span></h1>
      </div>
    </div>

    <div class="auth-inner" v-else-if="status === 'error'">
      <div class="panel">
        <p class="eyebrow">No pudimos continuar</p>
        <h1 class="lead">Invitación<br /><span class="lead-accent">inválida o vencida.</span></h1>
        <p class="note">{{ errorMsg }}</p>
        <router-link :to="{ name: 'login' }" class="btn-submit">
          <span>Ir a iniciar sesión</span>
          <span class="arrow" aria-hidden="true">→</span>
        </router-link>
      </div>
    </div>

    <div class="auth-inner" v-else>
      <div class="side">
        <p class="eyebrow">Invitación</p>
        <h1 class="lead">
          Te invitaron a<br />
          <span class="lead-accent">{{ invitation.organization }}</span>
        </h1>
        <p class="note">
          Vas a sumarte como <strong>{{ roleLabel }}</strong>. Completá tus datos para activar la
          cuenta.
        </p>
      </div>

      <form @submit.prevent="onSubmit" class="form" novalidate>
        <label class="field">
          <span class="field-label">Email</span>
          <input :value="invitation.email" disabled />
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
          <span>{{ loading ? "Activando cuenta..." : "Aceptar invitación" }}</span>
          <span v-if="!loading" class="arrow" aria-hidden="true">→</span>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getInvitation, acceptInvitation } from "../../api/accounts.api";
import { getPublicBranding } from "../../api/branding.api";
import { applyBranding, clearBranding } from "../../composables/useBranding";
import { useAuthStore } from "../../stores/auth.store";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const status = ref("loading");
const errorMsg = ref("");
const invitation = ref(null);

const firstName = ref("");
const lastName = ref("");
const password = ref("");
const loading = ref(false);
const error = ref("");

const roleLabel = computed(() => {
  if (invitation.value?.role === "ADMIN") return "Admin";
  if (invitation.value?.role === "AGENT") return "Técnico";
  return "Cliente";
});

function extractError(e) {
  return (
    e?.response?.data?.detail ||
    Object.values(e?.response?.data || {}).flat()[0] ||
    e.message ||
    "Error al aceptar la invitación"
  );
}

onMounted(async () => {
  if (route.params.slug) {
    try {
      const b = await getPublicBranding(route.params.slug);
      applyBranding(b);
    } catch (e) { /* sin branding */ }
  }

  try {
    invitation.value = await getInvitation(route.params.token);
    status.value = "ready";
  } catch (e) {
    errorMsg.value = extractError(e);
    status.value = "error";
  }
});

onUnmounted(() => {
  if (auth.user) applyBranding(auth.user.branding);
  else clearBranding();
});

async function onSubmit() {
  if (!firstName.value || !password.value) return;
  loading.value = true;
  error.value = "";
  try {
    await acceptInvitation(route.params.token, {
      first_name: firstName.value,
      last_name: lastName.value,
      password: password.value,
    });
    auth.loaded = false;
    await auth.loadMe();
    router.push(auth.redirectByRole());
  } catch (e) {
    error.value = extractError(e);
  } finally {
    loading.value = false;
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
.auth-inner:has(.panel) { grid-template-columns: 1fr; justify-items: center; text-align: center; }
.panel { max-width: 460px; }

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
.panel .note { margin: 0 auto 24px; }

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
.field input:disabled { color: var(--text-3); }

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
  text-decoration: none;
  box-shadow: 0 10px 28px -12px var(--accent-glow);
  transition: transform .12s, box-shadow .15s, opacity .15s;
}
.btn-submit:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 14px 30px -10px var(--accent-glow); }
.btn-submit:disabled { opacity: .55; cursor: not-allowed; }
.btn-submit .arrow { transition: transform .18s; }
.btn-submit:hover:not(:disabled) .arrow { transform: translateX(3px); }

@media (max-width: 800px) {
  .auth-inner { grid-template-columns: 1fr; gap: 40px; }
  .side { text-align: center; }
  .note { margin-left: auto; margin-right: auto; }
}
</style>
