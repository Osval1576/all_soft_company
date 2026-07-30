<template>
  <div class="page">
    <AppTopBar title="Base de conocimiento" />
    <div class="wrap">
      <header class="head">
        <div>
          <p class="eyebrow">Contenido</p>
          <h1 class="title">Base de conocimiento</h1>
        </div>
        <div class="head-actions">
          <router-link to="/admin/kb/sugerencias" class="btn-ghost">Sugerencias de IA</router-link>
          <button class="btn-new" @click="startNew">+ Nuevo artículo</button>
        </div>
      </header>

      <div v-if="loading" class="state">Cargando…</div>

      <div v-else class="layout">
        <!-- Lista -->
        <aside class="list">
          <p v-if="articles.length === 0" class="empty">Todavía no hay artículos.</p>
          <button
            v-for="a in articles"
            :key="a.id"
            class="list-item"
            :class="{ 'list-item--active': selected && selected.id === a.id }"
            @click="select(a)"
          >
            <span class="li-title">{{ a.title }}</span>
            <span class="li-badge" :class="a.is_published ? 'li-badge--pub' : 'li-badge--draft'">
              {{ a.is_published ? 'Publicado' : 'Borrador' }}
            </span>
          </button>
        </aside>

        <!-- Editor -->
        <section class="editor">
          <div v-if="!editing" class="editor-empty">
            Elegí un artículo de la lista o creá uno nuevo.
          </div>

          <form v-else class="card form" @submit.prevent="onSave">
            <label class="field">
              <span class="field-label">Título</span>
              <input v-model="form.title" placeholder="p. ej. Cómo restablecer tu contraseña" required />
            </label>

            <label v-if="form.slug" class="field">
              <span class="field-label">Slug</span>
              <input :value="form.slug" class="mono" disabled />
            </label>

            <label class="field">
              <span class="field-label">Contenido</span>
              <textarea v-model="form.body" rows="12" placeholder="Escribí el artículo…"></textarea>
            </label>

            <label class="field-check">
              <input type="checkbox" v-model="form.is_published" />
              <span>Publicado (visible para el agente de deflección y el portal)</span>
            </label>

            <div v-if="error" class="error-msg">{{ error }}</div>
            <div v-if="okMsg" class="ok-msg">{{ okMsg }}</div>

            <div class="actions">
              <button type="submit" :disabled="saving" class="btn-submit">
                {{ saving ? "Guardando…" : (isNew ? "Crear artículo" : "Guardar cambios") }}
              </button>
              <button
                v-if="!isNew"
                type="button"
                class="btn-delete"
                :disabled="saving"
                @click="onDelete"
              >Eliminar</button>
            </div>
          </form>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import AppTopBar from "../../../components/AppTopBar.vue";
import { listArticles, createArticle, updateArticle, deleteArticle } from "../../../api/kb.api";

const loading = ref(true);
const saving = ref(false);
const articles = ref([]);
const selected = ref(null);
const editing = ref(false);
const isNew = ref(false);
const error = ref("");
const okMsg = ref("");

const form = reactive({ title: "", slug: "", body: "", is_published: false });

function extractError(e, fallback) {
  const data = e?.response?.data;
  if (!data) return fallback;
  if (typeof data === "string") return data;
  if (data.detail) return data.detail;
  const first = Object.values(data).flat()[0];
  return first || fallback;
}

async function load() {
  loading.value = true;
  try {
    articles.value = await listArticles();
  } finally {
    loading.value = false;
  }
}

function resetMessages() {
  error.value = "";
  okMsg.value = "";
}

function fill(a) {
  form.title = a?.title || "";
  form.slug = a?.slug || "";
  form.body = a?.body || "";
  form.is_published = a?.is_published || false;
}

function select(a) {
  resetMessages();
  selected.value = a;
  isNew.value = false;
  editing.value = true;
  fill(a);
}

function startNew() {
  resetMessages();
  selected.value = null;
  isNew.value = true;
  editing.value = true;
  fill(null);
}

async function onSave() {
  saving.value = true;
  resetMessages();
  try {
    const payload = { title: form.title, body: form.body, is_published: form.is_published };
    if (isNew.value) {
      const created = await createArticle(payload);
      okMsg.value = "Artículo creado.";
      await load();
      select(articles.value.find((x) => x.id === created.id) || created);
    } else {
      const updated = await updateArticle(selected.value.id, payload);
      okMsg.value = "Cambios guardados.";
      await load();
      select(articles.value.find((x) => x.id === updated.id) || updated);
    }
  } catch (e) {
    error.value = extractError(e, "No se pudo guardar el artículo.");
  } finally {
    saving.value = false;
  }
}

async function onDelete() {
  if (!selected.value) return;
  if (!window.confirm(`¿Eliminar "${selected.value.title}"? Esta acción no se puede deshacer.`)) return;
  saving.value = true;
  resetMessages();
  try {
    await deleteArticle(selected.value.id);
    editing.value = false;
    selected.value = null;
    await load();
  } catch (e) {
    error.value = extractError(e, "No se pudo eliminar.");
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.wrap { max-width: 960px; margin: 0 auto; padding: 24px 20px; display: flex; flex-direction: column; gap: 20px; }
.state, .empty { color: var(--text-3); font-size: 14px; }

.head { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; }
.eyebrow {
  font-family: var(--font-mono); font-size: 10px; letter-spacing: 2px;
  text-transform: uppercase; color: var(--text-3); margin: 0 0 6px;
}
.title { font-family: var(--font-display); font-size: 22px; font-weight: 600; color: var(--text); margin: 0; }

.btn-new {
  padding: 9px 16px; border-radius: var(--r-sm);
  background: var(--accent); color: var(--accent-fg);
  font-family: var(--font-display); font-size: 13px; font-weight: 600;
  white-space: nowrap; transition: background .15s;
}
.btn-new:hover { background: var(--accent-hover); }
.head-actions { display: flex; align-items: center; gap: 10px; }
.btn-ghost { padding: 9px 14px; border-radius: var(--r-sm); border: 0.5px solid var(--border); color: var(--text-2); font-size: 13px; white-space: nowrap; }
.btn-ghost:hover { background: var(--surface-2); }

.layout { display: grid; grid-template-columns: 280px 1fr; gap: 20px; align-items: start; }
@media (max-width: 720px) { .layout { grid-template-columns: 1fr; } }

.list { display: flex; flex-direction: column; gap: 6px; }
.list-item {
  display: flex; flex-direction: column; gap: 6px; align-items: flex-start;
  text-align: left; padding: 12px 14px;
  border: 0.5px solid var(--border); border-radius: var(--r-sm);
  background: var(--surface); cursor: pointer; transition: border-color .15s, background .15s;
}
.list-item:hover { background: var(--surface-2); }
.list-item--active { border-color: var(--accent); }
.li-title { font-size: 14px; color: var(--text); font-weight: 500; }
.li-badge {
  font-family: var(--font-mono); font-size: 9px; letter-spacing: 1px; text-transform: uppercase;
  padding: 2px 6px; border-radius: 4px;
}
.li-badge--pub { background: var(--c-resolved-bg, var(--surface-2)); color: var(--c-resolved, var(--accent)); }
.li-badge--draft { background: var(--surface-2); color: var(--text-3); }

.editor { min-width: 0; }
.editor-empty {
  color: var(--text-3); font-size: 14px; padding: 40px 0; text-align: center;
  border: 0.5px dashed var(--border); border-radius: var(--r);
}
.card { background: var(--surface); border: 0.5px solid var(--border); border-radius: var(--r); padding: 18px; }
.form { display: flex; flex-direction: column; gap: 4px; }

.field { display: flex; flex-direction: column; gap: 8px; border-bottom: 0.5px solid var(--border); padding: 14px 0 12px; transition: border-color .15s; }
.field:focus-within { border-bottom-color: var(--accent); }
.field-label { font-family: var(--font-mono); font-size: 10px; letter-spacing: 1.5px; text-transform: uppercase; color: var(--text-3); }
.field input, .field textarea {
  background: transparent; border: none; outline: none; padding: 4px 0 2px;
  font-family: var(--font-body); font-size: 15px; color: var(--text); resize: vertical;
}
.field input.mono { font-family: var(--font-mono); font-size: 13px; color: var(--text-3); }
.field input::placeholder, .field textarea::placeholder { color: var(--text-3); }

.field-check { display: flex; align-items: center; gap: 10px; padding: 14px 0; font-size: 14px; color: var(--text); cursor: pointer; }
.field-check input { cursor: pointer; }

.error-msg { margin: 10px 0 0; padding: 9px 12px; border-radius: var(--r-sm); background: var(--c-urgent-bg); color: var(--c-urgent); font-size: 12px; }
.ok-msg { margin: 10px 0 0; padding: 9px 12px; border-radius: var(--r-sm); background: var(--c-resolved-bg, var(--surface-2)); color: var(--c-resolved, var(--accent)); font-size: 12px; }

.actions { display: flex; gap: 10px; margin-top: 16px; }
.btn-submit {
  padding: 10px 20px; border-radius: var(--r-sm);
  background: var(--accent); color: var(--accent-fg);
  font-family: var(--font-display); font-size: 14px; font-weight: 600;
  transition: background .15s, opacity .15s;
}
.btn-submit:hover:not(:disabled) { background: var(--accent-hover); }
.btn-submit:disabled { opacity: .55; cursor: not-allowed; }
.btn-delete {
  padding: 10px 16px; border-radius: var(--r-sm);
  background: transparent; border: 0.5px solid var(--border);
  color: var(--c-urgent); font-size: 14px; transition: background .15s;
}
.btn-delete:hover:not(:disabled) { background: var(--c-urgent-bg); }
.btn-delete:disabled { opacity: .55; cursor: not-allowed; }
</style>
