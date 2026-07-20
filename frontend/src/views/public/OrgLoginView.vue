<template>
  <LoginView :brand-name="brandName" :brand-logo="brandLogo" />
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from "vue";
import { useRoute } from "vue-router";
import LoginView from "../LoginView.vue";
import { getPublicBranding } from "../../api/branding.api";
import { applyBranding, clearBranding } from "../../composables/useBranding";
import { useAuthStore } from "../../stores/auth.store";

const route = useRoute();
const auth = useAuthStore();
const brandName = ref("AllSafe");
const brandLogo = ref(null);

async function resolveBranding() {
  try {
    const b = await getPublicBranding(route.params.slug);
    brandName.value = b.display_name || "AllSafe";
    brandLogo.value = b.logo_url || null;
    applyBranding(b);
  } catch (e) { /* 404 -> marca producto */ }
}

onMounted(resolveBranding);

watch(
  () => route.params.slug,
  (newSlug, oldSlug) => {
    if (newSlug !== oldSlug) resolveBranding();
  }
);

onUnmounted(() => {
  if (auth.user) applyBranding(auth.user.branding);
  else clearBranding();
});
</script>
