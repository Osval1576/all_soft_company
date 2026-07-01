<template>
  <div id="top" class="public-shell">
    <PublicHeader />
    <main><router-view /></main>
    <PublicFooter />
  </div>
</template>

<script setup>
import PublicHeader from "../components/public/PublicHeader.vue";
import PublicFooter from "../components/public/PublicFooter.vue";
</script>

<style scoped>
.public-shell { min-height: 100vh; background: var(--bg); color: var(--text); }
</style>
