# Métricas + Dashboards · F3 — Cumplimiento de SLA y satisfacción CSAT

**Fecha:** 2026-07-09
**Sub-proyecto:** F3 (tercera y última parte de F — SLAs + CSAT + métricas)
**Estado:** Diseño aprobado, pendiente de plan de implementación

## Objetivo

Dar visibilidad agregada del desempeño del soporte, consumiendo los datos que ya dejaron F1
(`TicketSla`) y F2 (`CSATResponse`): cumplimiento de SLA (1ª respuesta y resolución), tiempos
medios laborales, satisfacción CSAT y tendencias en el tiempo. Dos audiencias:

- **Admin — global:** desempeño del equipo entero, incluyendo ranking por técnico.
- **Técnico — personal:** su propio desempeño, con la media del equipo como referencia.

F3 es **puro read/agregación**: no crea modelos nuevos; agrega sobre `Ticket`, `TicketSla` y
`CSATResponse`.

## Contexto técnico relevante (estado actual)

- **Greenfield para métricas** — no existe app ni endpoint de métricas.
- **Datos disponibles:**
  - `TicketSla` (OneToOne con `Ticket`, `related_name="sla"`): `fr_level` y `res_level` ∈
    `{ok, at_risk, breached, met}`; `first_response_met_at`, `resolved_at` (timestamps reales);
    `first_response_due_at`, `resolution_due_at` (deadlines); `*_budget_min` (presupuestos).
  - `CSATResponse` (OneToOne con `Ticket`, `related_name="csat"`): `score` 1-5, `comment`,
    `created_at`.
  - `Ticket`: `Priority` (LOW/MEDIUM/HIGH/URGENT), `Status` (OPEN/IN_PROGRESS/RESOLVED/CLOSED),
    `asignado_a` (FK a user), `creado_por`, `created_at`, `reference`.
- **Motor de calendario (F1)** en `sla/calendar_engine.py`:
  - `get_calendar()` → construye un `Calendar` leyendo `SlaConfig` (singleton) + `Holiday` (2
    queries). **Se construye una sola vez por request** y se pasa a las funciones puras.
  - `business_minutes_between(a, b, cal) -> int` → minutos laborales entre dos instantes,
    respetando ventana L-V 9-18 y feriados. Devuelve `0` si `b <= a`.
- **Patrón de desacople (F1/F2):** las apps add-on (`sla`, `csat`) nunca son importadas por
  `tickets_t` a nivel de módulo. `metrics/` sigue el mismo patrón: importa de `tickets_t`, `sla`
  y `csat`, pero nadie la importa a ella a nivel de módulo.
- **Permisos:** `tickets_t/permissions.py` ya define `IsAdmin`, `IsAgent`, `IsCustomer`
  (`BasePermission` sobre `request.user.role`). F3 los reutiliza. (Existe además `IsAdminRole`
  duplicado en `sla/` y `landing_cms/` — follow-up de consolidación conocido, fuera de alcance
  de F3.)
- **Frontend:** router role-gated (`src/router/index.js`); `/admin/sla` (`AdminSla.vue`) es el
  patrón de "pantalla de admin dedicada". No hay librería de gráficos instalada (sólo `gsap`).
- **Caveat de infra conocido:** `SlaConfig.get_solo()` hace `get_or_create(pk=1)` — en tests con
  `TransactionTestCase` la tabla se puede truncar; los tests de métricas deben crear su propia
  `SlaConfig`/`SlaPolicy` en `setUp()` en vez de depender del seed de migración.

## Decisiones tomadas en el brainstorm

1. **Audiencia:** Admin global + Técnico personal (dos vistas, gating por rol en backend).
2. **Ventana temporal:** selector **7 / 30 / 90 días**; el endpoint recibe `?window=<n>` y filtra
   por `Ticket.created_at >= now - n días`.
3. **Cálculo de tiempos medios:** **minutos laborales** vía `business_minutes_between` (misma vara
   que el cumplimiento de SLA de F1) — no wall-clock.
4. **Gráficos:** librería **ApexCharts** (`vue3-apexcharts`), tematizada a la paleta azul
   eléctrico. (Se prefirió una librería sobre SVG a mano; ApexCharts sobre ECharts por menor peso
   y wrapper Vue 3 oficial.)
5. **Ranking por técnico:** **sí**, visible sólo para Admin.
6. **Vista del técnico:** sus propios números **+ media del equipo como línea de referencia**
   (no 100 % aislada).

## Arquitectura

### Backend — app nueva `metrics/`

```
backend/metrics/
  __init__.py
  apps.py
  services.py      # funciones de agregación PURAS (queryset + window + cal -> dict)
  views.py         # dos APIViews con gating por rol
  urls.py          # /api/metrics/admin/  y  /api/metrics/me/
  tests.py
```

Sin `models.py` propio (no hay modelos nuevos). Se registra en `INSTALLED_APPS` y su `urls.py`
se incluye bajo `/api/metrics/` en `config/urls.py`.

#### `services.py` — funciones puras

Todas reciben un **queryset base de `Ticket`** (ya filtrado por ventana y, para la vista del
técnico, por `asignado_a`), más el `Calendar`, y devuelven dicts serializables. No tocan
`request`. Firmas:

- `compliance(tickets_qs) -> {"first_response": pct|None, "resolution": pct|None}`
  **Cumplimiento honesto calculado desde timestamps vs deadlines, NO desde `fr_level`/`res_level`.**
  Ver la nota crítica abajo sobre por qué el campo de nivel no sirve para esto.
  - `first_response` = `count(first_response_met_at <= first_response_due_at) /
    count(first_response_met_at IS NOT NULL AND first_response_due_at IS NOT NULL)`.
    Denominador = tickets que **recibieron** primera respuesta (con deadline definido).
  - `resolution` = `count(resolved_at <= resolution_due_at) /
    count(resolved_at IS NOT NULL AND resolution_due_at IS NOT NULL)`.
    Denominador = tickets **resueltos** (con deadline definido).
  - Ambos se calculan en DB con agregación condicional comparando dos columnas datetime
    (`Q(sla__resolved_at__lte=F("sla__resolution_due_at"))`).
  - Denominador 0 → `None` (se renderiza como "—", no como 0 %).
- `avg_times(tickets_qs, cal) -> {"first_response_min": float|None, "resolution_min": float|None}`
  Media de `business_minutes_between(created_at, first_response_met_at, cal)` sobre tickets con
  `first_response_met_at` no nulo; ídem `resolution_min` con `resolved_at`. Baja a memoria sólo
  los pares de timestamps necesarios (`.values_list`), no instancias completas.
- `csat_summary(tickets_qs) -> {"average": float|None, "count": int, "distribution": {1..5: int}}`
  `Avg(score)` y conteo por score, agregado en DB sobre `csat`.
- `volume_totals(tickets_qs) -> {"total": int, "resolved": int, "open": int}`
  Conteos por `Status` (agregado en DB).
- `trend(tickets_qs) -> [{"date": "YYYY-MM-DD", "created": int, "resolved": int}, ...]`
  Serie diaria dentro de la ventana: creados por fecha de `created_at`, resueltos por fecha de
  `resolved_at`. Rellena días sin datos con ceros para que la línea sea continua.
- `technician_ranking(tickets_qs, cal) -> [{"technician_id", "name", "resolved", "sla_pct",
  "csat_avg", "avg_resolution_min"}, ...]`
  Agrupa por `asignado_a`; una fila por técnico con tickets asignados en la ventana. Ordenado
  por `sla_pct` desc (los sin desenlace al final).

**⚠️ Nota crítica — `fr_level`/`res_level` NO sirven para cumplimiento histórico:** en
`sla/signals.py`, la primera respuesta y la resolución setean el nivel a `"met"`
**incondicionalmente** (aunque sea tarde), y el `checker` sólo marca `breached`/`at_risk` en
tickets todavía OPEN/IN_PROGRESS (nunca pisa un `"met"`). Consecuencia: un ticket **resuelto
tarde queda `res_level="met"`**. Por eso `compliance()` calcula desde los timestamps reales vs
los deadlines (`resolved_at <= resolution_due_at`), no desde el campo de nivel. El campo de nivel
sigue siendo correcto para el badge en vivo de F1 (semáforo del ticket abierto), pero mezclaría
"a tiempo" con "tarde" en el agregado histórico. (Este es un quirk de F1, no se corrige en F3.)

**Regla anti-N+1 (lección de F1/F2):** cualquier iteración en Python que toque `t.sla`/`t.csat`
debe partir de un queryset con `.select_related("sla", "csat")`. Donde se pueda, agregar en DB
(`Count(Case(When(...)))`, `Avg`) en vez de iterar. `avg_times` y `technician_ranking` (que
necesitan el motor de calendario, no expresable en SQL) usan `.values_list(...)` para traer sólo
las columnas de timestamp, no instancias.

#### `views.py` — dos endpoints

- `GET /api/metrics/admin/?window=<7|30|90>` — `permission_classes = [IsAuthenticated, IsAdmin]`.
  Construye `cal = get_calendar()` una vez, arma `qs = Ticket.objects.select_related("sla",
  "csat").filter(created_at >= corte)`, y devuelve:
  ```json
  {
    "window": 30,
    "totals": { "total": ..., "resolved": ..., "open": ... },
    "compliance": { "first_response": 0.92, "resolution": 0.85 },
    "avg_times": { "first_response_min": 34.2, "resolution_min": 512.7 },
    "csat": { "average": 4.3, "count": 40, "distribution": {"1":1,"2":2,"3":5,"4":12,"5":20} },
    "trend": [ { "date": "2026-06-10", "created": 3, "resolved": 2 }, ... ],
    "ranking": [ { "technician_id": 5, "name": "...", "resolved": 12, "sla_pct": 0.9,
                   "csat_avg": 4.5, "avg_resolution_min": 480.0 }, ... ]
  }
  ```
- `GET /api/metrics/me/?window=<7|30|90>` — `permission_classes = [IsAuthenticated, IsAgent]`.
  Mismo `cal`, pero `qs_self = qs.filter(asignado_a=request.user)`. Devuelve los mismos bloques
  que Admin **excepto `ranking`**, y agrega `benchmark` = compliance/avg_times/csat calculados
  sobre el queryset del equipo entero (todos los técnicos, misma ventana) para comparar:
  ```json
  {
    "window": 30,
    "totals": {...}, "compliance": {...}, "avg_times": {...}, "csat": {...}, "trend": [...],
    "benchmark": { "compliance": {...}, "avg_times": {...}, "csat": { "average": 4.1 } }
  }
  ```

**Validación de `window`:** sólo `{7, 30, 90}`; cualquier otro valor o ausente → **default 30**
(lenient, sin 400). Un único helper `_parse_window(request)` compartido por ambos endpoints.

### Frontend

- **Dependencia nueva:** `vue3-apexcharts` + `apexcharts`.
- **Store/servicio:** `metrics.service.js` (axios `withCredentials`) con `getAdminMetrics(window)`
  y `getMyMetrics(window)`.
- **Componentes reutilizables** (`src/components/metrics/`):
  - `MetricTile.vue` — tile de KPI (label + valor grande + unidad; estado "—" si `null`).
  - `WindowSelector.vue` — toggle 7/30/90, emite `change`.
  - `SlaGauge.vue` — `radialBar` de ApexCharts (% cumplimiento).
  - `CsatBars.vue` — barras de distribución 1-5 + promedio.
  - `TrendLine.vue` — línea creados vs resueltos.
  - `TechRankingTable.vue` — tabla de ranking (sólo Admin).
- **Vistas contenedoras:**
  - `src/views/dashboards/AdminMetrics.vue` → ruta `/admin/metricas` (rol ADMIN), hermana de
    `/admin/sla`.
  - `src/views/dashboards/TechnicianMetrics.vue` → ruta `/tecnico/metricas` (rol AGENT). Muestra
    los KPIs propios con el `benchmark` del equipo como línea/valor de referencia; sin ranking.
- **Tematización ApexCharts:** un módulo `apexTheme.js` con los colores azul eléctrico, fuentes
  (Space Grotesk / JetBrains Mono para números), sin grid pesado, hairlines — para que los
  gráficos no rompan la estética v2. Copy en voseo.
- **Navegación:** enlace a "Métricas" en el layout/nav de Admin (junto a SLA) y en el de Técnico.

## Flujo de datos

1. La vista monta → llama al servicio con la ventana actual (default 30).
2. El endpoint construye el `Calendar` una vez, filtra el queryset por ventana (+ técnico), corre
   las funciones de `services.py`, devuelve el JSON agregado.
3. La vista distribuye cada bloque a su componente. Cambiar la ventana en `WindowSelector`
   re-fetchea.

## Manejo de errores y bordes

- **Sin datos en la ventana:** todos los agregados devuelven `None`/`[]`/`0` de forma explícita;
  el frontend muestra "—" o un estado vacío ("Sin datos en este período"), nunca un 0 % engañoso
  ni un gráfico roto.
- **División por cero:** encapsulada en cada función de `services.py` (denominador 0 → `None`).
- **Técnico sin tickets asignados:** `qs_self` vacío → KPIs en "—", pero el `benchmark` del equipo
  sí se muestra.
- **Error de red en el front:** estado de error visible en la vista (no `alert()`), con opción de
  reintentar; sin romper el resto del dashboard.

## Testing (TDD)

- **`services.py` (unit):** fixtures con timestamps fabricados y `SlaConfig`/`SlaPolicy` creados
  en `setUp()` (no depender del seed de migración). Asserts de valores **exactos**:
  - cumplimiento con mezcla de `met`/`breached`/`ok` → pct esperado y `None` cuando denominador 0.
  - `avg_times` cruzando noche/finde → minutos laborales exactos (misma técnica que
    `CalendarTests` de F1).
  - `csat_summary` distribución y promedio.
  - `trend` rellena días sin datos con ceros.
  - `technician_ranking` agrupa y ordena correctamente.
- **Endpoints (integration):** gating de rol — Admin entra a `/admin/`, Agent recibe 403 en
  `/admin/`; Agent en `/me/` ve sólo sus tickets + `benchmark`; Customer recibe 403 en ambos.
  Validación de `window`. Anti-N+1: `assertNumQueries` acotado en el listado (mismo patrón que
  `test_ticket_list_avoids_n_plus_one_on_sla`).
- **Frontend:** build limpio (`npm run build`) + verificación manual en navegador de ambas vistas
  con datos sembrados.

## Fuera de alcance (posibles F3.5 / futuro)

- Vista de métricas para el Cliente.
- Export CSV/PDF de reportes.
- Filtros adicionales (por prioridad, por cliente) más allá de la ventana temporal.
- Consolidar `IsAdminRole` duplicado (follow-up global, no de F3).

Ver [[allsafe-project-state]] y [[allsafe-conventions]].
