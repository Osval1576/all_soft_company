import { computed } from "vue";
import { useLocaleStore } from "../stores/locale.store";

export function usePick() {
  const store = useLocaleStore();
  const locale = computed(() => store.locale);
  function pick(obj, field) {
    if (!obj) return "";
    return obj[`${field}_${locale.value}`] ?? "";
  }
  return { pick, locale };
}
