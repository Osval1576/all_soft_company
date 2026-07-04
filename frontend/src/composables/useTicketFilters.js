import { ref, computed, unref } from "vue";

const PRIORITY_RANK = { LOW: 0, MEDIUM: 1, HIGH: 2, URGENT: 3 };

export function useTicketFilters(ticketsRef) {
  const estado = ref("");        // "" = todos
  const prioridad = ref("");
  const asignado = ref("");      // "" = todos, "none" = sin asignar, o id (string)
  const sortKey = ref("created_at");
  const sortDir = ref("desc");   // "asc" | "desc"

  function toggleSort(key) {
    if (sortKey.value === key) {
      sortDir.value = sortDir.value === "asc" ? "desc" : "asc";
    } else {
      sortKey.value = key;
      sortDir.value = "asc";
    }
  }

  function sortValue(t, key) {
    if (key === "prioridad") return PRIORITY_RANK[t.prioridad] ?? -1;
    if (key === "created_at" || key === "updated_at") return new Date(t[key]).getTime();
    return (t[key] ?? "").toString().toLowerCase();
  }

  const result = computed(() => {
    let list = [...unref(ticketsRef)];
    if (estado.value) list = list.filter((t) => t.estado === estado.value);
    if (prioridad.value) list = list.filter((t) => t.prioridad === prioridad.value);
    if (asignado.value === "none") {
      list = list.filter((t) => !t.asignado_a);
    } else if (asignado.value) {
      list = list.filter((t) => String(t.asignado_a) === String(asignado.value));
    }
    const key = sortKey.value;
    const dir = sortDir.value === "asc" ? 1 : -1;
    list.sort((a, b) => {
      const va = sortValue(a, key);
      const vb = sortValue(b, key);
      if (va < vb) return -1 * dir;
      if (va > vb) return 1 * dir;
      return 0;
    });
    return list;
  });

  return { estado, prioridad, asignado, sortKey, sortDir, toggleSort, result };
}
