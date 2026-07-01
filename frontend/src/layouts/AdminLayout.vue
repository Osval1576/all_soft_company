<template>
  <div class="adm">
    <aside class="adm-side">
      <div class="brand">AllSafe</div>
      <nav>
        <div class="group">Tickets</div>
        <router-link to="/admin">Dashboard</router-link>

        <div class="group">Sitio web</div>
        <router-link to="/admin/sitio/contenido">Contenido</router-link>
        <router-link to="/admin/sitio/equipo">Equipo</router-link>
        <router-link to="/admin/sitio/ubicaciones">Ubicaciones</router-link>
      </nav>
    </aside>
    <section class="adm-main"><router-view /></section>
  </div>
</template>

<style scoped>
.adm { display: grid; grid-template-columns: 240px 1fr; min-height: 100vh; }
.adm-side { background: var(--surface); border-right: 1px solid var(--border); padding: 20px 16px; }
.adm-side .brand { font-weight: 700; margin-bottom: 24px; }
.adm-side .group { font-size: 11px; text-transform: uppercase; color: var(--text-3); margin: 16px 0 6px; letter-spacing: .5px; }
.adm-side nav a { display: block; padding: 8px 10px; color: var(--text-2); text-decoration: none; border-radius: var(--r-sm); font-size: 14px; }
.adm-side nav a:hover, .adm-side nav a.router-link-active { background: var(--surface-2); color: var(--text); }
.adm-main { padding: 28px 32px; }
</style>
