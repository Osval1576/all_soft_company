# Progress Ledger — feat/landing-publica-cms

Branch created from main at ed8b1b4 on 2026-06-30.
Plan: docs/superpowers/plans/2026-06-30-allsafe-landing-publica.md

## Completed tasks

Task 1: complete (commits f771be3..8f5766a, review clean)
Task 2: complete (commits 8f5766a..789e1a5, 1 fix pass, review clean)
Task 3: complete (commits 789e1a5..4081101, review clean)
Task 4: complete (commits 4081101..b5aefa8, review clean)
Task 5: complete (commits b5aefa8..d28f7fb, review clean)
Task 6: complete (commits d28f7fb..d076086, review clean)
Task 7: complete (commits d076086..4b5d10d, review clean)
Task 8: complete (commits 4b5d10d..8a4705a, review clean)
Task 9: complete (commits 8a4705a..d8baa12, review clean)
Task 10: complete (commits d8baa12..a2147b6, 1 fix pass, review clean)
Task 11: complete (commits a2147b6..2c51d3f, review clean)
Task 12: complete (commits 2c51d3f..6a37050, 1 fix pass for vuedraggable@4)
Task 13: complete (commits 6a37050..a7a586e, review clean)
Task 14: complete (commits a7a586e..508a2f1, review clean)
Task 15: complete (commits 508a2f1..cc62f78, review clean)
Task 15: (rectify) complete
Task 16: complete (commits cc62f78..27237d0, review clean)
Task 17: complete (commits 27237d0..02f293b, 1 fix pass for ScrollTrigger cleanup)
Task 18: complete (commits 02f293b..21e1c67, review clean)
Task 19: complete (commits 21e1c67..c9d6ec3, review clean)
Task 20: complete (commits c9d6ec3..3a3c416, review skipped: trivial visual)
Task 21: complete (commits 3a3c416..cff6358, review skipped: transcription + build passes)
Task 22: complete (commits cff6358..ca736e4, review skipped: transcription)
Task 23: complete (commits ca736e4..396e670, review skipped: transcription + build passes)
Task 24: complete (commits 396e670..59e6236, review skipped: transcription + build passes)
Task 25: complete (commits 59e6236..5cfeabc)
Task 26: complete (commits 5cfeabc..c3ce522)
Task 27: complete (commits c3ce522..9d249d1)
Task 28: complete (commits 9d249d1..efbd4e0, backend suite 25/25 OK)

## Summary
All 28 implementation tasks + 1 fix pass on Task 2, 1 on Task 10, 1 on Task 12 (vuedraggable v4), 1 on Task 17 (ScrollTrigger cleanup). Backend suite 25/25 tests OK. Frontend builds clean.

Final review + 5-commit fix wave: complete (commits efbd4e0..e6638a9, 30/30 backend tests OK, build clean)


---

# Sub-proyecto Dashboards v2 · Fase 1 (Core)

Branch: feat/dashboards-v2-fase1 (creada por Task 1)
Plan: docs/superpowers/plans/2026-07-01-dashboards-v2-fase1-core.md

## Completed tasks

(mergeado a main, 44/44 tests)

---

# Sub-proyecto Dashboards v2 · Fase 2 (Comunicación)

Branch: feat/dashboards-v2-fase2-comunicacion (creada desde main en e3317920 el 2026-07-03).
Plan: docs/superpowers/plans/2026-07-03-dashboards-v2-fase2-comunicacion.md
Spec: docs/superpowers/specs/2026-07-03-dashboards-v2-fase2-comunicacion-design.md

## Completed tasks

Task 1: complete (commits 22d9c222..b5e3fab3, review clean)
Task 2: complete (commits a3849209..b92507d1, review clean)
Task 3: complete (commits 05e12fa8..3f402645, review clean; minor nits: import os a media altura + falta newline final en settings.py — para barrido final)
Task 4: complete (commits 94924643..1e865197, review clean; minor: sin logging en el except del group_send en services.py — considerar logger.exception en barrido final)
Task 5: complete (commits 3273c0a3..ec4fc618, 1 fix pass: daphne==4.2.2 en requirements; deviación TestCase->TransactionTestCase adjudicada como aceptada por async DB de channels/MySQL; suite 14/14)
Task 6: complete (commits bdc0f0a5..566a8689, review clean; minor style nits: get_object idiomático vs hand-rolled 404 — no bloqueante)
Task 7: complete (commits f36de4d7..f085c412, review clean; implementer se colgó sin commitear -> controller verificó (IntegrationTests 2/2, StateTransitionTests dirigido 1/1) y commiteó. PENDIENTE review final: correr suite backend COMPLETA off-hours (MySQL ~30-80s/test hace timeout la suite entera en 10 min).)
Task 8: complete (commits 471b87bd..ec25bd80, build limpio, review approved). FINDINGS plan-mandated para fix wave final en notifications.store.js: (a) spread order `{toastId:id, ...n}` -> `{...n, toastId:id}`; (b) markRead/markAllRead no revierten el optimistic update si el POST falla (catch vacío); (c) backoff abandona tras 5 intentos sin recovery (igual que useWsConnection de chat — consistente, opcional).
Task 9: complete (commits ba5cd4f7..912acc0e, build limpio, review approved; sólo nits cosméticos)
Task 10: complete (commits ccacf9c1..a2187232, 1 fix pass: bug Critical plan-mandated — bell no abría por bubbling al document, arreglado con @click.stop; build limpio). FINDINGS para fix wave final: dashboardRoute() duplicado en NotificationBell/ToastContainer/auth.store (extraer helper); sin a11y (Escape/role=dialog) en dropdown.
Task 11: complete (commits b7daa208..f3be721a, build limpio, review approved). FINDINGS para fix wave final: NotificationSettings.vue onToggle/onMounted no manejan error del PATCH/GET (sin rollback ni feedback) — plan-mandated.

## Estado: 11/11 tasks completas.

Review final de rama (opus): NEEDS FIXES -> merge-blocker arreglado.
- Fix merge-blocker (commit 5ec8b651): aislar dispatch() en create_message del consumer con try/except + logging; un fallo de notificaciones ya NO puede romper la entrega del chat. También logging en el except del group_send de services.py (_push).
- #9 proceso: suite backend COMPLETA corrida (background, 752s) -> 65/65 OK, cero regresiones. Merge-blockers despejados; rama merge-ready.

Follow-ups aceptados por el review final (NO bloquean merge; para un ciclo posterior):
- store.js: spread order {toastId:id,...n}->{...n,toastId:id}; markRead/markAllRead sin rollback en fallo; backoff sin recovery (igual que useWsConnection).
- NotificationSettings.vue: onToggle/onMounted sin manejo de error del PATCH/GET.
- dashboardRoute() duplicado x3 + redirectByRole -> extraer helper.
- Inconsistencia rol backend (role) vs frontend (is_staff/is_superuser) -> estandarizar en `role` del /api/me/.
- settings.py: import os a media altura + falta newline final (y asgi.py).
- Bell dropdown a11y (Escape/role=dialog).
- CAVEAT deploy (release notes): LocMemCache + InMemoryChannelLayer son per-process; NO mergear a entorno multi-proceso hasta Redis (sub-proyecto G).

