<template>
  <draggable :model-value="items" @update:model-value="onUpdate" item-key="id" handle=".handle">
    <template #item="{ element }">
      <div class="row">
        <span class="handle">⋮⋮</span>
        <slot :item="element" />
      </div>
    </template>
  </draggable>
</template>

<script setup>
import draggable from "vuedraggable";
defineProps({ items: { type: Array, required: true } });
const emit = defineEmits(["reorder"]);
function onUpdate(newList) {
  emit("reorder", newList.map(x => x.id));
}
</script>

<style scoped>
.row { display: flex; align-items: center; gap: 10px; padding: 8px; border: 1px solid var(--border); border-radius: var(--r); margin-bottom: 6px; background: var(--surface); }
.handle { cursor: grab; color: var(--text-3); user-select: none; }
</style>
