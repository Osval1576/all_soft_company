<template>
  <div class="drop" :class="{drag: drag}"
       @dragover.prevent="drag=true" @dragleave="drag=false"
       @drop.prevent="onDrop">
    <img v-if="previewUrl" :src="previewUrl" alt="" class="preview" />
    <p v-else class="hint">Arrastra o <label>elige una imagen<input type="file" accept="image/*" @change="onPick" /></label></p>
    <button v-if="previewUrl" type="button" class="clear" @click="clear">×</button>
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue";
const props = defineProps({ file: File, existingUrl: String });
const emit = defineEmits(["update:file"]);
const drag = ref(false);
const localUrl = ref(null);

const previewUrl = computed(() => localUrl.value || props.existingUrl || "");

function onPick(e) { setFile(e.target.files[0]); }
function onDrop(e) { drag.value = false; setFile(e.dataTransfer.files[0]); }
function setFile(f) {
  if (!f) return;
  emit("update:file", f);
  if (localUrl.value) URL.revokeObjectURL(localUrl.value);
  localUrl.value = URL.createObjectURL(f);
}
function clear() {
  emit("update:file", null);
  if (localUrl.value) URL.revokeObjectURL(localUrl.value);
  localUrl.value = null;
}
</script>

<style scoped>
.drop { position: relative; border: 1px dashed var(--border); border-radius: var(--r); padding: 16px; text-align: center; min-height: 100px; display: grid; place-items: center; }
.drop.drag { border-color: var(--accent); background: var(--accent-light, transparent); }
.preview { max-width: 100%; max-height: 160px; border-radius: var(--r-sm); }
.hint { color: var(--text-3); font-size: 13px; }
.hint label { color: var(--accent); cursor: pointer; }
.hint input { display: none; }
.clear { position: absolute; top: 6px; right: 6px; border: 1px solid var(--border); background: var(--surface); border-radius: 50%; width: 24px; height: 24px; cursor: pointer; }
</style>
