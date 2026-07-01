<template>
  <footer class="pf">
    <div class="pf-inner">
      <span>© {{ year }} AllSafe</span>
      <nav>
        <a href="#features">{{ $t("nav.features") }}</a>
        <a href="#about">{{ $t("nav.about") }}</a>
        <a href="#contacto">{{ $t("nav.contact") }}</a>
      </nav>
    </div>
  </footer>
</template>

<script setup>
const year = new Date().getFullYear();
</script>

<style scoped>
.pf { border-top: 1px solid var(--border); padding: 24px; color: var(--text-3); font-size: 13px; margin-top: 60px; }
.pf-inner { max-width: 1180px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; }
.pf nav a { color: var(--text-3); text-decoration: none; margin-left: 20px; }
.pf nav a:hover { color: var(--text); }
</style>
