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

Fase 2 mergeada a main (merge 1c1f1ed2) y pusheada a origin/main el 2026-07-04.

---

# Sub-proyecto Dashboards v2 · Fase 3 (Enriquecimiento)

Branch: feat/dashboards-v2-fase3-enriquecimiento (creada desde main en 4499e6a2 el 2026-07-04).
Plan: docs/superpowers/plans/2026-07-04-dashboards-v2-fase3-enriquecimiento.md
Spec: docs/superpowers/specs/2026-07-04-dashboards-v2-fase3-enriquecimiento-design.md

Pre-flight: nit DRY conocido — can_access_ticket (T2) coexiste con user_can_access_ticket del consumer; el plan no refactoriza el consumer. Para triaje en el review.

## Completed tasks

Task 1: complete (commits e4853af0..c2c1cea7, review clean; fixture PNG del brief estaba corrupta -> reemplazada por PNG 1x1 válido en _png_bytes(); 4/4 + suite tickets_t 18/18). Minors informativos: validador confía en content-type (mitigado por PIL.verify + firma %PDF); sin test de límites de tamaño (heredado del brief) — para barrido final.
Task 2: complete (commits 22087974..5184509f, review approved; 3/3 + suite 21/21). FINDING para fix wave final: DRY — can_access_ticket (permissions.py) duplica user_can_access_ticket del consumer; consolidar (que el consumer llame al helper). Plan lo dejó fuera de scope a propósito.
Task 3: complete (commits d0719073..72149227, review approved; 6/6 + suite 27/27; broadcast+dispatch best-effort aislados, notif test verifica fila real). Sólo nits triviales.
Task 4: complete (commits aafb1571..c27d9a72, review approved; 3/3 + suite 30/30; IDOR cerrado con filter(pk, ticket), bytes verificados byte-a-byte). Backend de adjuntos completo.
Task 5: complete (commits 4099af53..80ff7b33, build limpio, review approved; sin duplicado local+WS, canSend correcto). Minor plan-mandated: error de upload usa alert() en vez de toast/inline — para barrido final si se quiere pulir.
Task 6: complete (commits 1dcef3d0..2e101c3e, build limpio, review approved; cross-origin OK — imágenes/PDF vía fetch-blob, objectURLs revocados). Adjuntos completo T1-T6. Minor DRY: prettySize duplicado en ChatPanel.vue y MessageAttachment.vue — para barrido final.
Task 7: complete (commits a63efcac..4bf2b60d, build limpio, review approved; filtro/orden sólido). Minors inherentes al plan: NaN en fechas inválidas / prioridad desconocida -> rank -1 (ok para datos bien formados).
Task 8: complete (commits 4a8ac742..f86c5f18, build limpio, review approved; columnas 8/8, búsqueda combinada con filtros, sin filteredTickets colgado).
Task 9: complete (commits 1497330a..fe17b413, build limpio, review approved; grid 2-col intacto, Pool/stats sin tocar). FINDING para fix wave final: el dropdown de orden del Técnico no alterna dirección (re-seleccionar la misma opción no dispara @change) -> queda asc por clave; el Admin sí alterna con headers.

## Estado: 9/9 tasks completas.

Review final de rama (opus): **READY para merge** — sin merge-blockers (a diferencia de Fase 2). IDOR cerrado, sin fuga de MEDIA, best-effort aislado, objectURLs limpios, payload consistente end-to-end (serializer + message_to_payload). Backend sin cambios desde el full run de tickets_t 30/30 (Task 4); tasks 5-9 fueron sólo frontend. Suite backend COMPLETA corrida (background, 925s) -> **81/81 OK** (65 Fase 2 + 16 adjuntos), cero regresiones. Rama merge-ready.

Follow-ups aceptados (NO bloquean; ciclo futuro):
- Consumer text-path no usa message_to_payload (divergencia latente del "single source of truth") -> refactor: create_message devuelve el instance y broadcast vía message_to_payload. Agrupar con:
- DRY can_access_ticket vs user_can_access_ticket del consumer -> que el consumer llame al helper.
- prettySize duplicado (ChatPanel/MessageAttachment) -> util compartido.
- alert() en errores de upload/download -> migrar a toast (Fase 2 ya tiene sistema de toasts).
- Dropdown de orden del Técnico no alterna dirección (asc-only por clave) -> bind sortDir a control explícito.
- Validador confía en content_type (mitigado por PIL.verify + %PDF) -> content-sniffing real en G.
- Sin test de límites de tamaño (>2MB img / >10MB pdf).
- nosniff header en download + trailing newlines -> G/hardening.

Fase 3 mergeada a main (merge 58f9161f) y pusheada a origin/main el 2026-07-04.

---

# Sub-proyecto SLA · F1 (Motor de SLA + semáforo)

Branch: feat/sla-f1-motor (creada desde main en f1d56ad8 el 2026-07-04).
Plan: docs/superpowers/plans/2026-07-04-sla-f1-motor.md
Spec: docs/superpowers/specs/2026-07-04-sla-f1-motor-design.md

Pre-flight fix: AppConfig renombrado a SlaAppConfig (evita colisión con el modelo SlaConfig).
F se descompone en F1(SLA)/F2(CSAT)/F3(métricas); este ciclo es F1.

## Completed tasks

Task 1: complete (commits 6cd71bd8..2b2cb350, review approved; 3/3). Implementer murió sin commitear -> controller verificó (ModelTests 3/3) y commiteó. signals.py es stub intencional (Task 4 lo llena). El implementer revivió después, re-implementó de cero y confirmó byte-idéntico (sin dup). Minor: import `settings` sin usar en models.py (heredado del plan) -> barrido final.
Task 2: complete (commits d9fc5e94..81fc3ebb, review approved; 8/8 calendario + suite 11/11, sin editar tests). FINDING Important LATENTE para review final: _start_of/_end_of usan aritmética wall-clock -> en TZ con DST, día de transición (23/25h) da ±1h de error. NO bloquea (default Mexico_City no observa DST desde 2022). Fix futuro: validar TZ no-DST o math DST-aware. Minors: minutes=0/negativos sin test/guarda.
Task 3: complete (commits fb202cd7..c2bd6c54, review approved; 4/4 + suite 15/15; precedencia met>breached>at_risk>ok correcta, None-guard OK). Minors: gaps de cobertura heredados del brief (branch None, reloj res) — negligible.
Task 4: complete (commits a2726f95..53f463eb, review approved; 6/6 + regresión sla+tickets_t 51/51). 2 fixes fuera de lista validados como correctos: (a) get_solo() refresh_from_db arregla bug real de Task 1 (TimeField default string no casteado en get_or_create -> rompía calendar_engine); (b) ajuste del test onetoone de Task 1 por colisión con el signal auto-create. Signals desacoplan sla<-tickets_t. Note: _agent_or_admin incluye is_superuser (consistente con el resto del codebase).
Task 5: complete (commits ffac9d6f..d0b2fdab, review approved sin issues; 2/2 + notifications 23/23). SLA in-app only (email=False, no toca presence/prefs), dedup agente+admins. FINDING menor test-hygiene para review final: los TransactionTestCase de notifications truncan SlaPolicy sembrada -> el signal loguea "sin SlaPolicy para prioridad MEDIUM" (benigno, degradación elegante). Fix opcional: sembrar policy en esos tests o bajar el log level.
Task 6: complete (commits accb21dc..66eb34ef, review approved; 2/2 + suite 23/23 + smoke check_sla OK). Idempotencia rank-based (advance-only, met skip, OPEN/IN_PROGRESS), scheduler con RUN_MAIN guard + daemon + loop try/except. Minor: import Ticket sin usar en checker.py (del brief) -> barrido final.
Task 7: complete (commits 5e1812d3..039ae234, review approved; 1/1). Implementer murió sin commitear -> controller verificó (1/1) y commiteó. Calendario memoizado por request (DRF comparte el context en listas). Minor: except:pass sin logging en get_serializer_context -> considerar logger.warning en barrido final.
Task 8: complete (commits ab9189c5..c7adac7f, review approved; 4/4 + suite 28/28). FINDING Important plan-mandated para fix wave final: IsAdminRole duplicado byte-a-byte de landing_cms.permissions (ya 3 copias admin-role en el codebase) -> hoistear a un módulo común. Minor: PATCH policies puede dar 500 en rename de prioridad (edge case, la UI no renombra).
Task 9: complete (commits 69579d00..b2d709bf, build limpio, review approved; columnas Admin 9/9/9 consistentes, CSS vars OK, null-safe). Minors cosméticos (props sin usar, labelFor edge con due pasado).
Task 10: complete (commits bb2a08b0..05e76492, build limpio, review approved; api client mapea Task 8, ruta admin-sla con role guard, load/save consistente). Minors pre-existentes/plan-driven: sin manejo de error en save/delete, sin confirm en delete holiday, work_days sin hint de formato.

## Estado: 10/10 tasks completas.

Review final de rama (opus): NEEDS FIXES (soft) -> 1 merge-blocker Important arreglado.
- Fix (commit 0f3fe4e3): N+1 en `sla` -> `select_related("sla")` en get_queryset base + pool; + guard `if action != "create"` y `logger.warning` en get_serializer_context. Test nuevo assertNumQueries(3) en SerializerSlaTests (confirmado 2/2 post-fix por el fixer). select_related es neutral en comportamiento.
- Sin import cycle (sla<-tickets_t sólo lazy), idempotencia sólida, degradación elegante, migration graph limpio. Los 8 findings diferidos triageados como follow-up aceptable (DST latente, IsAdminRole dup, imports sin usar, except sin log, test-hygiene, AdminSla UX, cobertura, PATCH 500 edge).
- Gate pre-merge: suite backend COMPLETA (pre-fix) -> 111/111 OK (2749s; 81 previos + 30 SLA), cero regresiones.
- Post-fix sla+tickets_t con --keepdb dio 3 fails + 9 errors PERO es artefacto de --keepdb: los TransactionTestCase de la corrida completa previa truncaron la SlaPolicy sembrada por migración, y --keepdb no re-siembra -> todos los fails son seed-dependent ("sin SlaPolicy"). NO es regresión del fix (select_related es neutral). Suite COMPLETA con --noinput (DB fresca re-siembra) -> **112/112 OK** (1243s; 111 + test N+1). GATE DE MERGE EN VERDE. Rama merge-ready.
- ELEVAR finding #5 (test-hygiene): el seed por migración es frágil ante TransactionTestCase+--keepdb. Fix: crear las SlaPolicy en setUp de los tests seed-dependent (no depender del seed de migración).

FINDINGS diferidos acumulados (para triaje del review final):
1. [Important latente] DST wall-clock en calendar_engine (_start_of/_end_of) -> ±1h en día de transición si TZ observa DST. Default Mexico_City NO observa DST -> safe hoy. Fix: validar TZ no-DST o math DST-aware.
2. [Important plan-mandated] IsAdminRole duplicado (sla.admin_views vs landing_cms.permissions; +helper en tickets_t) -> hoistear a módulo común.
3. [Minor] imports sin usar: settings en sla/models.py, Ticket en sla/checker.py.
4. [Minor] except:pass sin logging en TicketViewSet.get_serializer_context.
5. [Minor test-hygiene] TransactionTestCase de notifications trunca SlaPolicy -> warning "sin SlaPolicy". Sembrar policy o bajar log level.
6. [Minor] AdminSla.vue: sin manejo de error en save/delete, sin confirm en delete, work_days sin hint.
7. [Minor] compute_levels sin test de branch None / reloj res (heredado del brief).
8. [Minor] PATCH policies puede dar 500 en rename de prioridad (edge, UI no renombra).

SLA F1 mergeado a main (merge 8b1c9b4b) y pusheado a origin/main el 2026-07-05.

---

# Sub-proyecto CSAT · F2 (Encuesta de satisfaccion in-app)

Branch: feat/csat-f2 (creada desde main en e15fcf4a el 2026-07-05).
Plan: docs/superpowers/plans/2026-07-05-csat-f2.md
Spec: docs/superpowers/specs/2026-07-05-csat-f2-design.md

Pre-flight: sin conflictos, plan escaneado limpio.

## Completed tasks
