<template>
  <footer class="pf">
    <div class="pf-inner">
      <div class="pf-brand">
        <span class="pf-mark">AS</span>
        <span class="pf-year">© {{ year }} AllSafe</span>
      </div>

      <nav class="pf-nav">
        <a href="#about">{{ $t("nav.about") }}</a>
        <a href="#locations">{{ $t("nav.locations") }}</a>
        <a href="#contacto">{{ $t("nav.contact") }}</a>
        <router-link to="/login">{{ $t("nav.signin") }}</router-link>
      </nav>

      <div class="pf-status">
        <span class="pf-dot" aria-hidden="true"></span>
        <span>hecho con calma</span>
      </div>
    </div>
  </footer>
</template>

<script setup>
const year = new Date().getFullYear();
</script>

<style scoped>
.pf {
  border-top: 0.5px solid var(--border);
  padding: 28px 32px;
  background: var(--bg);
}
.pf-inner {
  max-width: 1240px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 32px;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--text-3);
}
.pf-brand { display: inline-flex; align-items: center; gap: 10px; }
.pf-mark {
  width: 22px;
  height: 22px;
  background: var(--surface-2);
  color: var(--text-2);
  border-radius: 4px;
  display: grid;
  place-items: center;
  font-family: var(--font-display);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.5px;
}
.pf-year { letter-spacing: 1.5px; }

.pf-nav { display: inline-flex; gap: 24px; justify-content: center; }
.pf-nav a, .pf-nav .router-link-active {
  color: var(--text-3);
  text-decoration: none;
  letter-spacing: 1.5px;
  transition: color .15s;
}
.pf-nav a:hover { color: var(--text); }

.pf-status {
  justify-self: end;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.pf-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
  animation: pf-pulse 2.4s ease-in-out infinite;
}
[data-theme="dark"] .pf-dot { box-shadow: 0 0 6px var(--accent-glow); }
@keyframes pf-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }
@media (prefers-reduced-motion: reduce) { .pf-dot { animation: none; } }

@media (max-width: 700px) {
  .pf-inner { grid-template-columns: 1fr; text-align: center; gap: 18px; }
  .pf-brand, .pf-status { justify-self: center; }
}
</style>
