<template>
  <LoginView :brand-name="brandName" :brand-logo="brandLogo" />
</template>

<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import { useRoute } from "vue-router";
import LoginView from "../LoginView.vue";
import { getPublicBranding } from "../../api/branding.api";
import { applyBranding, clearBranding } from "../../composables/useBranding";
import { useAuthStore } from "../../stores/auth.store";

const route = useRoute();
const auth = useAuthStore();
const brandName = ref("AllSafe");
const brandLogo = ref(null);

onMounted(async () => {
  try {
    const b = await getPublicBranding(route.params.slug);
    brandName.value = b.display_name || "AllSafe";
    brandLogo.value = b.logo_url || null;
    applyBranding(b);
  } catch (e) { /* 404 -> marca producto */ }
});

onUnmounted(() => {
  if (!auth.user) clearBranding();
});
</script>
