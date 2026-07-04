<template>
  <div class="toast-stack" aria-live="polite">
    <TransitionGroup name="toast">
      <button
        v-for="t in store.toasts"
        :key="t.toastId"
        class="toast"
        @click="onClick(t)"
      >
        <span class="toast-dot" aria-hidden="true"></span>
        <span class="toast-body">
          <span class="toast-title">{{ t.title }}</span>
          <span v-if="t.body" class="toast-sub">{{ t.body }}</span>
        </span>
        <span class="toast-close" @click.stop="store.dismissToast(t.toastId)">✕</span>
      </button>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { useRouter } from "vue-router";
import { useNotificationsStore } from "../../stores/notifications.store";
import { useAuthStore } from "../../stores/auth.store";

const store = useNotificationsStore();
const auth = useAuthStore();
const router = useRouter();

function dashboardRoute() {
  if (auth.user?.is_superuser) return { name: "admin" };
  if (auth.user?.is_staff) return { name: "tecnico-inbox" };
  return { name: "cliente" };
}

function onClick(t) {
  store.markRead(t.id);
  store.dismissToast(t.toastId);
  const target = dashboardRoute();
  if (t.ticket) target.query = { ticket: t.ticket };
  router.push(target);
}
</script>

<style scoped>
.toast-stack {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 340px;
}
.toast {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  text-align: left;
  padding: 12px 14px;
  background: var(--surface);
  border: 0.5px solid var(--border);
  border-left: 2px solid var(--accent);
  border-radius: var(--r);
  cursor: pointer;
  color: var(--text);
}
.toast:hover { background: var(--surface-2); }
.toast-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--accent); margin-top: 5px; flex-shrink: 0;
}
.toast-body { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.toast-title { font-family: var(--font-display); font-weight: 600; font-size: 13px; }
.toast-sub {
  font-size: 12px; color: var(--text-2);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.toast-close { margin-left: auto; color: var(--text-3); font-size: 12px; }
.toast-enter-active, .toast-leave-active { transition: all .25s ease; }
.toast-enter-from { opacity: 0; transform: translateX(20px); }
.toast-leave-to { opacity: 0; transform: translateX(20px); }
</style>
