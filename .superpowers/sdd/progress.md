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

Task 1: complete (commits ee0fa757..9b326af6, review clean; 2/2, OneToOne+IntegrityError verificado real). Nits estilísticos triviales (comment default, __str__ usa ticket_id).
Task 2: complete (commits fd1808c6..33d6c461, review clean; 4/4 + suite 6/6). Primer intento murió casi de inmediato (5 tool uses) sin tocar el árbol -> re-despachado limpio sin necesidad de recovery.
Task 3: complete (commits 494b9b98..b5dbbae9, review clean; 6/6 + suite 12/12). Orden de checks verificado: dueño (403) antes que elegibilidad (400) — el punto de seguridad más delicado, correcto.
Task 4: complete (commits 397daafc..ebb88ece, review clean; 4/4 + regresión csat+tickets_t 46/46). Backend de CSAT completo T1-T4. can_rate correctamente AND de 3 condiciones, import lazy verificado (sin import csat a nivel de módulo en tickets_t), csat visible cross-role.
Task 5: complete (commits ea0b9315..f0a1f5c8, build limpio, review clean; transcripción exacta). Minors cosméticos: estrellas sin :disabled durante submit; sin focus-visible custom.
Task 6: complete (commits bd214535..00bd3e41, build limpio, review clean; banner condicional mutuamente exclusivo, layout flex-column verificado sin regresión, ChatPanel sigue pass-through). Minor cosmético: dos divs .csat-banner redundantes (tal como lo especifica el brief).
Task 7: complete (commits 31573e97..46361909, build limpio, review clean; onStatusChange preservado en Technician, ambos handlers guardan selectedTicket null, list-sync correcto por id). Verificación manual (Step 4) diferida — nota de proceso, no bloquea.
Task 8: complete (commits de01f451..a6254695, build limpio, review clean). Implementer murió sin commitear -> controller verificó build limpio y commiteó; agente revivió después y confirmó byte-idéntico. Conteo de columnas verificado (10 th/10 td/colspan=10). 8/8 tasks completas.

## Estado: 8/8 tasks completas.

Review final de rama (opus): READY. Un finding nuevo Minor pero recomendado como fix ahora (N+1 en csat, mismo patrón que sla en F1) -> aplicando select_related("sla","csat").
- Orden de checks de seguridad verificado (404->403->400->409->400 score) sin leak de estado a extraños.
- Decoupling limpio (sin import csat a nivel de módulo en tickets_t), csat_payload como única fuente de verdad (endpoint + serializer llaman la misma función).
- can_rate seguro (guard sin request/no-auth), frontend sync correcto (selectedTicket + lista), columnas Admin 10/10/10.
- Los 5 findings conocidos (estrellas sin disabled, sin focus-visible, verificación manual diferida T7/T8, 2 divs banner redundantes, patrón CsatDisplay vs SlaBadge) triageados como follow-up aceptable.
Suite backend COMPLETA (pre-fix, 128 tests) -> 1 fail + 2 errors. Diagnosticado: (a) el fail es assertNumQueries(3) de SLA F1, roto porque en el código pre-fix el queryset no tenía select_related("csat") -> N+1 exacto que el fix de csat resuelve; (b) los 2 errors son MySQLdb Lock wait timeout por CONCURRENCIA auto-infligida (corrí la suite completa al mismo tiempo que el fixer corría su propio test contra el mismo DB) -> no son bugs de código.
Re-run sla+tickets_t con --keepdb: sigue fallando pero por el MISMO artefacto de seed-truncation ya diagnosticado en F1 (SlaConfig singleton borrado por TransactionTestCase previo + --keepdb no re-siembra). CONFIRMADO que el fix es correcto: la query 7 ahora hace un solo LEFT OUTER JOIN con sla_ticketsla Y csat_csatresponse (N+1 resuelto).
sla+tickets_t+csat con --noinput (DB fresca) -> **75/75 OK** (1143s). Confirma que el fix del N+1 es correcto y todos los fails previos eran artefactos de --keepdb/concurrencia, no bugs reales. GATE DE MERGE EN VERDE. Rama merge-ready.

---
# F3 · Metricas + Dashboards (rama feat/metrics-f3, iniciada 2026-07-09)
Plan: docs/superpowers/plans/2026-07-09-metrics-f3.md
Base de rama: 6cadba44
Task 1: complete (commits 6cadba44..0fc37e3c, review clean; 4/4). DONE_WITH_CONCERNS: MySQL AVG() trunca a 4 dec -> test relajado a places=3 (legitimo, verificado por reviewer). Minors: imports datetime/MX + self.tech sin usar aun (los usan T3/T5), csat_summary 2 queries (awareness T6).
Task 2: complete (commits 0fc37e3c..aef69527, review clean; 3/3 + metrics 7/7). Cumplimiento desde timestamps (met_at<=due_at) verificado, denom-0->None, OneToOne descarta fan-out del select_related. Minors plan-mandated: falta test de 1a-respuesta tarde y de null parcial (cobertura, para review final).
Task 3: complete (commits aef69527..d8116f23 + fix 4a907727, review clean; AvgTimesTests 3/3, metrics 10/10). Important plan-mandated resuelto: agregado test que cruza fin de semana (vie17->lun10 = 120 min laborales, no 3900 wall-clock) -> confirma que avg_times usa el motor de calendario. Minor: DRY de las 2 ramas de values_list (verbatim del brief, no tocar).
Task 4: complete (commits 4a907727..383c1e0d + fix 5793358c, review clean; TrendTests 2->3, metrics 12/12). Important plan-mandated resuelto: agregado test que setea sla.resolved_at -> cubre la rama de resueltos de trend (resolved-sum=1). Minor plan-mandated: 2 llamadas a timezone.now() (start/end) - non-issue en la practica.
Task 5: complete (commits 5793358c..0d75a765 + fix f708393b, review clean; RankingTests 1->2, metrics 14/14). Codigo verificado correcto (group-by seguro por OneToOne, sort None-last, denom-None, name sin query extra, loop acotado por #tecnicos). Important resuelto: test que cubre sla_pct None + orden None-al-final + csat_avg None + avg_resolution_min.
Task 6: complete (commits f708393b..4ac0844a + fix 2e47003c, review clean; EndpointTests 5/5, metrics 19/19). Codigo verificado: gating correcto (Customer 403 ambos, Admin 403 me/, Agent 403 admin/), benchmark sobre team (no self), Calendar unico por request, window default 30, wiring lazy. Important resuelto: test anti-N+1 era tautologia -> reescrito (mide pocos vs muchos tickets mismo tecnico, mismo conteo) -> ahora SI detecta N+1. Minor: benchmark values no asertados en test (codigo correcto). BACKEND F3 COMPLETO.
Task 7: complete (commit 2e47003c..56320737, review clean; build limpio). Verbatim del brief, api client sigue convencion (http withCredentials), endpoints cross-checkeados contra backend urls, scope puro scaffold. Minor: chunk apexcharts ~509kb (tradeoff aceptado, eleccion del usuario).
Task 8: complete (commit 56320737..8e2b4955, review clean; build limpio). 6 componentes verbatim, imports resuelven a exports reales de T7, null/empty-states presentes (SlaGauge/CsatBars/TechRankingTable), CsatBars maneja keys 1 y "1" (guard JSON). Minor: TrendLine sin empty-state (chart vacio renderiza ok, verbatim del brief).
Task 9: complete (commit 8e2b4955..c8ef5006, review clean; build limpio, SIN issues). Vista Admin: props cross-checkeados contra source real de cada componente, ruta gated ADMIN sibling de /admin/sla, nav link agregado, null/loading/error states presentes (retry sin alert), refetch en cambio de ventana.
Task 10: complete (commit c8ef5006..7a4ad589, review clean; build limpio, SIN issues). Vista Tecnico: benchmark en hints (data.benchmark.*), NO ranking (verificado ausente), ruta gated AGENT, nav .tech-nav agregado, null-guard via fmt helpers, error retry sin alert. Shape cross-checkeado contra MyMetricsView. TODAS LAS 10 TASKS COMPLETAS.

## Estado: 10/10 tasks completas. Minors acumulados para triage del review final:
- T2: falta test 1a-respuesta tarde + null parcial (cobertura).
- T4: 2 timezone.now() start/end (non-issue).
- T6: benchmark values no asertados en test (codigo correcto).
- T7: bundle apexcharts ~509kb (tradeoff aceptado).
- T8/T10: TrendLine sin empty-state; apexTheme no re-tematiza en toggle light/dark con vista abierta (follow-up).

Barrido de follow-ups (rama chore/follow-ups-sweep, 2026-07-11/12): 16 commits (A1-A7 backend + B1-B11 frontend). Review de rama: Approved, 18/18 items, 0 Critical/Important. Gate: suite completa fresca 150/150 OK (147 + 3 tests nuevos del barrido). Verificacion browser: B9 re-theme confirmado en vivo (strokes cambian con data-theme, 4 charts sobreviven el remount); F3 dashboards PASS pre-barrido. Backend implementer murio sin reporte -> controller verifico commits + corrio suite. Nota: HMR de Vite corrompe la sesion del browser si se edita con el dev server vivo -> reiniciar server tras sweeps grandes.


---
# G · Endurecimiento Produccion (rama feat/produccion-g, iniciada 2026-07-12)
Plan: docs/superpowers/plans/2026-07-12-produccion-g.md
Base de rama: 5624b565
G-T1: complete (commits 5624b565..88e04c8b + fix 8c8675f6, users 3/3 + sla 29/29 + tickets_t 31/31 + metrics 21/21). Desvio aceptado: @register(deploy=True) (el check plano rompia manage.py test) -> T7 entrypoint DEBE correr check --deploy. Fix real encontrado por el switch de TZ: TruncDate+CONVERT_TZ devuelve NULL sin tz-tables de MySQL (tambien en la imagen Docker!) -> trend bucketea en Python con localdate.
G-T1: review clean (Approved). Minors cross-task: T4 checks nuevos deben seguir convencion deploy=True; T7 entrypoint DEBE invocar check --deploy o el guard nunca corre. trend() Python-loop OK a esta escala.
G-T2: complete (commit e7b829a4, review Approved; check limpio + notifications 23/23). Pins reales: channels-redis 4.3.0, django-redis 7.0.0 (compat verificada contra el source instalado). Minors para T7: pinnear redis transitivo (8.0.1); runbook debe incluir smoke de 4 puntos del branch Redis (check con REDIS_URL, cache round-trip, WS cross-worker, Redis caido -> 5xx ruidoso).
G-T3: complete (commit 69053e01, review Approved; sla 31/31). Implementer murio sin commitear -> controller verifico diff verbatim + corrio suite + commiteo. Loop semantics hand-traced OK (max-loops sin sleep final, KeyboardInterrupt limpio, excepcion no mata loop, get_solo caido -> fallback 10min).
G-T4: complete (commit 88f2a5ff, review Approved sin issues; users+tickets_t 36/36). SECURE_REDIRECT_EXEMPT regex verificado contra el source del middleware (path sin slash inicial); dev neutral comprobado setting por setting; sin referencias colgadas a /admin/ viejo.
G-T5: complete (commits d23340f1 + fix 2cdc0347, review Approved; users 5/5, migrate dev OK, build limpio). Backfill verificado en 4 casos (super->ADMIN, staff->AGENT, correctos intactos, idempotente). Fix wave: 4 sitios residuales de flags migrados a role (dashboardRoute, NotificationSettings, AppTopBar, filtro de agentes de AdminDashboard que podia listar ADMINs como asignables). Unico is_staff restante = payload de creacion de usuario (escritura, no gating).
G-T6: complete (commit 4ec791f8; build limpio). Diff de 12 lineas verificado directo por el controller (?? no ||, doc en .env.example) - reviewer omitido por escala, lo cubre el review final de rama.
G-T7: complete (commits b338965c + fix 8fb91ae9, review opus Approved; YAML valido, env contract cerrado, cadena compose-settings-nginx-asgi hand-traced sin defectos de boot). 3 enmiendas cross-task aplicadas (check --deploy en entrypoint, redis pinneado, smoke Redis 4 puntos). Fix wave: smoke Redis-down real (cache.set + WS, no /api/health/), mysql healthcheck CMD-SHELL, .dockerignore, .gitattributes eol, TLS sin vhost 80 residual, caveat de scale.

## G: 7/7 tasks completas. Pendiente: review final de rama + gate DB fresca + merge.
Review final de rama G (opus): READY TO MERGE, sin blockers. 2 minors arreglados inline (utcnow->localdate en prefijo de referencia, frontend/.dockerignore). Follow-up documentado: is_staff en payload de creacion de usuario (AdminDashboard:239 + UserCreateSerializer) - un ADMIN creado por el form no accede a /django-admin/ (probablemente intencional, django-admin via createsuperuser).
