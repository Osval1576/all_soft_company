---
name: verify
description: Receta para levantar y verificar AllSafe (Django+Vue) en el navegador
---

# Verificar AllSafe localmente

## Levantar
- `.claude/launch.json` ya define `backend` (Django :8000) y `frontend` (Vite :5173). Usar `preview_start` con cada nombre.
- Vite tarda ~30s la primera vez (re-optimiza deps si cambió el lockfile) — esperar antes de navegar o falla con "navigation denied".
- La DB de dev puede tener migraciones pendientes tras merges: `python manage.py migrate` primero.

## Datos y usuarios demo
- Script idempotente de seed: crear usuarios `demo_admin`/`demo_tech`/`demo_tech2` (AGENT)/`demo_cliente`, password `demo1234`, y tickets `DEMO-###` con SLA/CSAT variados. Patrón: ver git history o re-generar (usuarios necesitan `is_superuser`/`is_staff` además de `role` — el router del front gatea por esos flags, el backend por `role`).
- Login en `/login` (cookie-based; SameSite=Lax — el front y la API deben ser localhost).

## Gotchas
- **`computer screenshot` se cuelga (timeout 30s) en páginas con charts de ApexCharts** — el resto del browser funciona. Verificar con `read_page` (árbol de accesibilidad) y `javascript_tool` (dump de valores del DOM) en su lugar.
- Rutas clave: `/admin/metricas` (ADMIN), `/tecnico/metricas` (AGENT), `/admin/sla`, dashboards `/admin`, `/tecnico`, `/cliente`.
- Probe de gating: `fetch('/api/metrics/admin/', {credentials:'include'})` desde consola del rol equivocado → 403; navegar a ruta ajena → redirect por rol.
