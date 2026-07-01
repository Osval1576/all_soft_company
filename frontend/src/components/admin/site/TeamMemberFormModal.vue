<template>
  <div class="overlay" @click.self="$emit('close')">
    <div class="modal">
      <header><h3>{{ member?.id ? "Editar miembro" : "Agregar miembro" }}</h3><button @click="$emit('close')">×</button></header>
      <ImageDrop v-model:file="photoFile" :existingUrl="member?.photo" />
      <label>Nombre <input v-model="form.name" required /></label>
      <I18nField label="Cargo" v-model:es="form.role_es" v-model:en="form.role_en" />
      <I18nField label="Bio" type="textarea" v-model:es="form.bio_es" v-model:en="form.bio_en" />
      <label class="check"><input type="checkbox" v-model="form.is_active" /> Activo</label>
      <footer>
        <button @click="$emit('close')">Cancelar</button>
        <button class="primary" @click="save" :disabled="busy">{{ busy ? "..." : "Guardar" }}</button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import I18nField from "./I18nField.vue";
import ImageDrop from "./ImageDrop.vue";

const props = defineProps({ member: Object });
const emit = defineEmits(["close", "saved"]);

const form = reactive({
  name: props.member?.name || "",
  role_es: props.member?.role_es || "",
  role_en: props.member?.role_en || "",
  bio_es: props.member?.bio_es || "",
  bio_en: props.member?.bio_en || "",
  is_active: props.member?.is_active ?? true,
  order: props.member?.order ?? 0,
});
const photoFile = ref(null);
const busy = ref(false);

async function save() {
  busy.value = true;
  const fd = new FormData();
  Object.entries(form).forEach(([k, v]) => fd.append(k, v ?? ""));
  if (photoFile.value) fd.append("photo", photoFile.value);
  emit("saved", { id: props.member?.id, formData: fd });
  busy.value = false;
}
</script>

<style scoped>
.overlay { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: grid; place-items: center; z-index: 100; }
.modal { background: var(--surface); border-radius: var(--r-lg); padding: 24px; width: min(520px, 92vw); display: flex; flex-direction: column; gap: 12px; max-height: 90vh; overflow-y: auto; }
header { display: flex; justify-content: space-between; align-items: center; }
header h3 { margin: 0; font-size: 16px; }
header button { background: transparent; border: none; font-size: 22px; color: var(--text-3); cursor: pointer; }
label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--text-2); font-weight: 600; }
label.check { flex-direction: row; align-items: center; gap: 8px; font-weight: 400; }
input { padding: 8px 10px; border: 1px solid var(--border); border-radius: var(--r); background: var(--surface); color: var(--text); font-size: 14px; }
footer { display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px; }
footer button { padding: 8px 16px; border-radius: var(--r); border: 1px solid var(--border); background: var(--surface); color: var(--text); cursor: pointer; }
footer button.primary { background: var(--accent); color: var(--accent-fg); border-color: transparent; }
</style>
