<template>
  <div class="page">
    <AppTopBar title="Branding" />
    <div class="wrap">
      <div v-if="loading" class="state">Cargando…</div>
      <template v-else>
        <header class="head">
          <p class="eyebrow">Personalización</p>
          <h1 class="title">Branding de tu organización</h1>
        </header>

        <div v-if="locked" class="card upsell">
          <p>
            El branding está disponible en los planes <strong>Pro</strong> y <strong>Business</strong>.
          </p>
          <router-link :to="{ name: 'admin-suscripcion' }" class="upsell-link">Ver planes →</router-link>
        </div>

        <form v-else class="card form" @submit.prevent="onSave">
          <label class="field">
            <span class="field-label">Nombre visible</span>
            <input v-model="displayName" placeholder="p. ej. Acme Support" />
          </label>

          <label class="field">
            <span class="field-label">Color de acento</span>
            <div class="color-row">
              <input type="color" v-model="accentColor" class="color-swatch" />
              <input v-model="accentColor" class="hex" placeholder="#0038FF" />
            </div>
          </label>

          <label class="field field--file">
            <span class="field-label">Logo (PNG/JPEG/WebP, máx. 512 KB)</span>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              class="file-input"
              @change="onFile"
            />
            <img v-if="logoPreview" :src="logoPreview" class="preview" alt="Vista previa del logo" />
          </label>

          <label class="field-check">
            <input type="checkbox" v-model="defaultDark" />
            <span>Tema oscuro por defecto para usuarios nuevos</span>
          </label>

          <div v-if="error" class="error-msg">{{ error }}</div>
          <div v-if="okMsg" class="ok-msg">{{ okMsg }}</div>

          <button type="submit" :disabled="saving" class="btn-submit">
            {{ saving ? "Guardando..." : "Guardar branding" }}
          </button>
        </form>
      </template>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import AppTopBar from "../../components/AppTopBar.vue";
import { getBranding, saveBranding } from "../../api/branding.api";
import { getSubscription } from "../../api/billing.api";
import { applyBranding } from "../../composables/useBranding";
import { useAuthStore } from "../../stores/auth.store";

const MAX_LOGO_BYTES = 512 * 1024;

const auth = useAuthStore();
const loading = ref(true);
const displayName = ref("");
const accentColor = ref("#0038FF");
const defaultDark = ref(false);
const logoFile = ref(null);
const logoPreview = ref(null);
const locked = ref(false);
const saving = ref(false);
const error = ref("");
const okMsg = ref("");

function extractError(e, fallback) {
  const data = e?.response?.data;
  if (!data) return fallback;
  if (typeof data === "string") return data;
  if (data.detail) return data.detail;
  const first = Object.values(data).flat()[0];
  return first || fallback;
}

onMounted(async () => {
  try {
    const sub = await getSubscription();
    if (sub?.plan === "free") locked.value = true;
  } catch (_) {
    // si no se puede saber el plan, se intenta igual: el backend valida al guardar
  }

  try {
    const b = await getBranding();
    displayName.value = b.display_name || "";
    accentColor.value = b.accent_color || "#0038FF";
    defaultDark.value = b.default_dark || false;
    logoPreview.value = b.logo_url || null;
  } catch (_) {
    // se mantienen los valores por defecto
  } finally {
    loading.value = false;
  }
});

function onFile(ev) {
  const f = ev.target.files?.[0];
  if (!f) return;
  if (f.size > MAX_LOGO_BYTES) {
    error.value = "El logo no puede superar 512 KB.";
    ev.target.value = "";
    return;
  }
  error.value = "";
  logoFile.value = f;
  logoPreview.value = URL.createObjectURL(f);
}

async function onSave() {
  saving.value = true;
  error.value = "";
  okMsg.value = "";
  try {
    const fd = new FormData();
    fd.append("display_name", displayName.value);
    fd.append("accent_color", accentColor.value);
    fd.append("default_dark", defaultDark.value);
    if (logoFile.value) fd.append("logo", logoFile.value);
    const b = await saveBranding(fd);
    applyBranding(b);
    if (auth.user) auth.user.branding = b;
    okMsg.value = "Branding actualizado.";
  } catch (e) {
    if (e?.response?.status === 403) {
      locked.value = true;
    } else {
      error.value = extractError(e, "No se pudo guardar.");
    }
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped>
.wrap { max-width: 640px; margin: 0 auto; padding: 24px 20px; display: flex; flex-direction: column; gap: 20px; }
.state { color: var(--text-3); }

.head { display: flex; flex-direction: column; }
.eyebrow {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--text-3);
  margin: 0 0 6px;
}
.title { font-family: var(--font-display); font-size: 22px; font-weight: 600; color: var(--text); margin: 0; }

.card { background: var(--surface); border: 0.5px solid var(--border); border-radius: var(--r); padding: 18px; }

.upsell { display: flex; flex-direction: column; gap: 10px; color: var(--text-2); font-size: 14px; line-height: 1.5; }
.upsell-link { align-self: flex-start; color: var(--accent); font-weight: 600; text-decoration: none; }
.upsell-link:hover { text-decoration: underline; }

.form { display: flex; flex-direction: column; gap: 4px; }

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-bottom: 0.5px solid var(--border);
  padding: 14px 0 12px;
  transition: border-color .15s;
}
.field:focus-within { border-bottom-color: var(--accent); }

.field-label {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--text-3);
}

.field input:not([type="checkbox"]):not([type="color"]) {
  background: transparent;
  border: none;
  outline: none;
  padding: 4px 0 2px;
  font-family: var(--font-body);
  font-size: 15px;
  color: var(--text);
}
.field input::placeholder { color: var(--text-3); }

.color-row { display: flex; align-items: center; gap: 10px; }
.color-swatch { width: 36px; height: 36px; padding: 0; border: 0.5px solid var(--border); border-radius: var(--r-sm); background: transparent; cursor: pointer; }
.hex { flex: 1; font-family: var(--font-mono); letter-spacing: 0.5px; }

.file-input { font-size: 13px; color: var(--text-2); }
.preview { margin-top: 10px; max-height: 56px; max-width: 200px; object-fit: contain; border: 0.5px solid var(--border); border-radius: var(--r-sm); background: var(--surface-2); padding: 6px; }

.field-check {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 0;
  font-size: 14px;
  color: var(--text);
  cursor: pointer;
}
.field-check input { cursor: pointer; }

.error-msg {
  margin: 10px 0 0;
  padding: 9px 12px;
  border-radius: var(--r-sm);
  background: var(--c-urgent-bg);
  color: var(--c-urgent);
  font-size: 12px;
}

.ok-msg {
  margin: 10px 0 0;
  padding: 9px 12px;
  border-radius: var(--r-sm);
  background: var(--c-resolved-bg, var(--surface-2));
  color: var(--c-resolved, var(--accent));
  font-size: 12px;
}

.btn-submit {
  margin-top: 16px;
  align-self: flex-start;
  padding: 10px 20px;
  border-radius: var(--r-sm);
  background: var(--accent);
  color: var(--accent-fg);
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 600;
  transition: background .15s, opacity .15s;
}
.btn-submit:hover:not(:disabled) { background: var(--accent-hover); }
.btn-submit:disabled { opacity: .55; cursor: not-allowed; }
</style>
