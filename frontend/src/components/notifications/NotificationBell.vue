<template>
  <div class="bell-wrap">
    <button class="bell-btn" @click.stop="toggle" aria-label="Notificaciones">
      <i class="ti ti-bell" aria-hidden="true"></i>
      <span v-if="store.unreadCount > 0" class="bell-badge">{{ badgeText }}</span>
    </button>

    <div v-if="open" class="bell-panel" @click.stop>
      <div class="bell-head">
        <span>Notificaciones</span>
        <button v-if="store.unreadCount > 0" class="bell-readall" @click="store.markAllRead()">
          Marcar todas
        </button>
      </div>
      <div class="bell-list">
        <p v-if="store.items.length === 0" class="bell-empty">Sin novedades.</p>
        <button
          v-for="n in store.items.slice(0, 20)"
          :key="n.id"
          class="bell-item"
          :class="{ 'bell-item--unread': !n.is_read }"
          @click="onItem(n)"
        >
          <span class="bell-item-title">{{ n.title }}</span>
          <span v-if="n.body" class="bell-item-body">{{ n.body }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { useRouter } from "vue-router";
import { useNotificationsStore } from "../../stores/notifications.store";
import { useAuthStore } from "../../stores/auth.store";

const store = useNotificationsStore();
const auth = useAuthStore();
const router = useRouter();
const open = ref(false);

const badgeText = computed(() => (store.unreadCount > 9 ? "9+" : String(store.unreadCount)));

function toggle() {
  open.value = !open.value;
}

function dashboardRoute() {
  if (auth.user?.is_superuser) return { name: "admin" };
  if (auth.user?.is_staff) return { name: "tecnico-inbox" };
  return { name: "cliente" };
}

function onItem(n) {
  store.markRead(n.id);
  open.value = false;
  const target = dashboardRoute();
  if (n.ticket) target.query = { ticket: n.ticket };
  router.push(target);
}

function onDocClick() {
  open.value = false;
}
onMounted(() => document.addEventListener("click", onDocClick));
onBeforeUnmount(() => document.removeEventListener("click", onDocClick));
</script>

<style scoped>
.bell-wrap { position: relative; }
.bell-btn {
  width: 34px; height: 34px;
  border: 0.5px solid var(--border);
  border-radius: 6px;
  display: grid; place-items: center;
  color: var(--text-2); background: transparent; cursor: pointer;
  position: relative;
}
.bell-btn:hover { background: var(--surface-2); color: var(--text); }
.bell-btn i { font-size: 15px; }
.bell-badge {
  position: absolute; top: -4px; right: -4px;
  min-width: 16px; height: 16px; padding: 0 4px;
  background: var(--accent); color: var(--accent-fg);
  border-radius: 100px; font-size: 9px; font-weight: 700;
  display: grid; place-items: center;
}
.bell-panel {
  position: absolute; top: 42px; right: 0;
  width: 300px; max-height: 380px; overflow-y: auto;
  background: var(--surface); border: 0.5px solid var(--border);
  border-radius: var(--r); z-index: 1001;
}
.bell-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 12px; border-bottom: 0.5px solid var(--border);
  font-family: var(--font-display); font-weight: 600; font-size: 13px;
}
.bell-readall {
  font-size: 11px; color: var(--accent); background: transparent; cursor: pointer;
}
.bell-list { display: flex; flex-direction: column; }
.bell-empty { padding: 16px; text-align: center; color: var(--text-3); font-size: 13px; }
.bell-item {
  display: flex; flex-direction: column; gap: 2px;
  padding: 10px 12px; text-align: left; cursor: pointer;
  border-bottom: 0.5px solid var(--border); background: transparent; color: var(--text);
}
.bell-item:hover { background: var(--surface-2); }
.bell-item--unread { background: var(--accent-light); }
.bell-item-title { font-size: 13px; font-weight: 500; }
.bell-item-body {
  font-size: 12px; color: var(--text-2);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
</style>
