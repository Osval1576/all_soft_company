<template>
  <div class="att">
    <template v-if="att.is_image">
      <img
        v-if="objectUrl"
        :src="objectUrl"
        class="att-img"
        :alt="att.name"
        @click="openBlob"
      />
      <div v-else-if="error" class="att-error">No se pudo cargar la imagen</div>
      <div v-else class="att-loading">Cargando imagen…</div>
    </template>

    <button v-else class="att-file" @click="download">
      <span class="att-icon">📄</span>
      <span class="att-meta">
        <span class="att-name">{{ att.name }}</span>
        <span class="att-size">{{ prettySize(att.size) }}</span>
      </span>
      <span class="att-dl">↓</span>
    </button>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from "vue";
import { fetchAttachmentBlob } from "../../api/tickets.api";
import { prettySize } from "../../utils/prettySize.js";
import { useNotificationsStore } from "../../stores/notifications.store";

const props = defineProps({ att: { type: Object, required: true } });

const notif = useNotificationsStore();
const objectUrl = ref(null);
const error = ref(false);

async function loadImage() {
  try {
    const blob = await fetchAttachmentBlob(props.att.url);
    objectUrl.value = URL.createObjectURL(blob);
  } catch (_) {
    error.value = true;
  }
}

function openBlob() {
  if (objectUrl.value) window.open(objectUrl.value, "_blank");
}

async function download() {
  try {
    const blob = await fetchAttachmentBlob(props.att.url);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = props.att.name || "archivo";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (_) {
    notif.pushToast({ title: "No se pudo descargar el archivo.", tone: "error" });
  }
}

onMounted(() => { if (props.att.is_image) loadImage(); });
onBeforeUnmount(() => { if (objectUrl.value) URL.revokeObjectURL(objectUrl.value); });
</script>

<style scoped>
.att { margin-top: 4px; }
.att-img {
  max-width: 220px; max-height: 220px;
  border-radius: var(--r-sm);
  border: 0.5px solid var(--border);
  cursor: pointer;
  display: block;
}
.att-loading, .att-error { font-size: 12px; color: var(--text-3); }
.att-file {
  display: inline-flex; align-items: center; gap: 10px;
  padding: 8px 12px;
  border: 0.5px solid var(--border);
  border-radius: var(--r-sm);
  background: var(--surface-2);
  cursor: pointer;
  max-width: 240px;
}
.att-file:hover { background: var(--border); }
.att-icon { font-size: 18px; }
.att-meta { display: flex; flex-direction: column; min-width: 0; text-align: left; }
.att-name {
  font-size: 12px; font-weight: 500; color: var(--text);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.att-size { font-size: 10px; color: var(--text-3); font-family: var(--font-mono); }
.att-dl { margin-left: auto; color: var(--text-3); }
</style>
