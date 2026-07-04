<template>
  <router-view />
  <ToastContainer v-if="auth.user" />
</template>

<script setup>
import { watch } from "vue";
import { useAuthStore } from "./stores/auth.store";
import { useNotificationsStore } from "./stores/notifications.store";
import ToastContainer from "./components/notifications/ToastContainer.vue";

const auth = useAuthStore();
const notif = useNotificationsStore();

watch(
  () => auth.user,
  (user, prev) => {
    if (user && !prev) notif.init();
    if (!user && prev) notif.disconnect();
  },
  { immediate: true }
);
</script>
