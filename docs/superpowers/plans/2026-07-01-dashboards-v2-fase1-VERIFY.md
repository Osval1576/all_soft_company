# Dashboards v2 · Fase 1 — Verificación manual

## Backend
- [ ] `python backend/manage.py test tickets_t -v 2` → todos OK (14+ tests)
- [ ] `curl -X PATCH /api/tickets/{id}/ -d '{"asignado_a": <customer_id>}'` como ADMIN → 400 con mensaje "Solo se puede asignar a técnicos"
- [ ] `curl -X POST /api/tickets/{id}/take/` como CUSTOMER → 403
- [ ] `curl -X POST /api/tickets/{id}/take/` como AGENT (ticket sin asignar) → 200
- [ ] Segundo `take/` del mismo ticket con otro AGENT → 409

## Frontend / Cliente
- [ ] Loguear como CUSTOMER: no aparecen stat cards, se ven lista lateral + chat.
- [ ] Crear un nuevo ticket → aparece en la lista, se auto-selecciona.
- [ ] Abrir un ticket viejo: aparece el historial al pie del chat (colapsable).

## Frontend / Técnico
- [ ] Loguear como AGENT: dashboard con tabs, stat cards arriba.
- [ ] Tab "Pool disponible": ver tickets sin asignar. Click "Tomar" → ticket pasa a "Mis tickets", tab cambia automáticamente.
- [ ] Cambiar estado a IN_PROGRESS desde el select del ChatPanel → 200 y evento aparece en timeline.
- [ ] Intentar cambiar de RESOLVED a IN_PROGRESS → 400.

## Frontend / Admin
- [ ] Loguear como ADMIN: cards con hairline (sin shadow), typography v2.
- [ ] Assign dropdown solo muestra AGENTs.
- [ ] Cambiar CLOSED a OPEN → 200 (reopen ADMIN).

## Chat resiliente
- [ ] Abrir un ticket, badge verde "Conectado".
- [ ] Matar backend → badge naranja "Reconectando…" pulsante.
- [ ] Esperar ~30 s sin backend → badge gris "Desconectado" + botón "Reintentar".
- [ ] Arrancar backend, click "Reintentar" → verde "Conectado" de nuevo.

## Theme toggle
- [ ] Click sun/moon en topbar → cambia el theme. Persiste al recargar.
