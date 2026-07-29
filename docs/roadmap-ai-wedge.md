# Roadmap — Wedge de IA (AllSafe)

*Creado: 2026-07-27 · Estado: propuesta estratégica*

## Norte
> **"Mesa de ayuda con IA, en español, para PyMES y agencias de LATAM."**

El objetivo de este roadmap es convertir a AllSafe de "otro helpdesk" en un producto **AI-native** que aproveche el modelo de datos que ya existe (tickets, mensajes, eventos, SLA, CSAT, métricas). No competimos por paridad de features: competimos por **IA útil desde el día uno**, algo que los incumbentes hacen lento y caro.

## Principios guía
1. **La IA asiste, no reemplaza.** El agente siempre decide. Nada se envía al cliente sin acción humana en las primeras fases.
2. **AI-native, no add-on.** Se apoya en el modelo de datos actual (`tickets_t`, `sla`, `csat`), no en un bolt-on.
3. **Aislamiento multi-tenant estricto.** Los prompts/datos de una org NUNCA cruzan a otra. La IA respeta el scoping que ya audita el proyecto.
4. **Opt-in + gating por plan.** Cada org activa la IA; las features de IA son palanca de monetización (plan Pro/Business en `billing`).
5. **Costo bajo control.** Modelo barato (clase Haiku) para clasificar/rutear; modelo de calidad (clase Sonnet) para generar/resumir. Rate-limit y presupuesto por org.
6. **Evaluable.** Cada feature de IA nace con una métrica de éxito y un set de evaluación (no "parece que anda").

> Nota de implementación: al construir, cargar la skill `claude-api` para IDs de modelo vigentes, pricing, tool-use y prompt caching. Este doc es estratégico; no fija IDs de modelo.

---

## Fase 0 — Cimientos de IA *(habilitador, 1 sprint)*
Sin esto, ninguna feature es sostenible.

- **Gateway de IA aislado**: un único módulo `ai/` que habla con la API de Claude (mismo patrón que el gateway de Stripe en `billing`: un solo punto, mockeable, testeable).
- **Config por tenant**: modelo `OrgAiSettings` (opt-in, presupuesto mensual, idioma, tono). Gateado por `billing.effective_plan`.
- **Guardrails**: límites de tokens, timeout, fallback si la IA falla o el presupuesto se agotó (degradación elegante — el producto sigue funcionando sin IA).
- **Prompt-caching** del contexto estático (instrucciones + KB de la org) para bajar costo.
- **Auditoría/log** de llamadas de IA por org (para costo y debugging), sin filtrar datos entre tenants.
- **Métrica**: costo/ticket, latencia p95, tasa de error de la IA.

---

## Fase 1 — Quick wins de mayor ROI *(2 features, el corazón del wedge)*

### 1A) Auto-borrador de respuesta para el agente ⭐ (empezar acá)
- **Qué**: botón "Sugerir respuesta" en el `ChatPanel`; la IA redacta un borrador usando el hilo del ticket + datos del cliente. El agente edita y envía.
- **Dónde encaja**: `tickets_t` (mensajes del ticket) → gateway `ai/` → sugerencia en el ChatPanel (WebSocket/REST).
- **Por qué primero**: máximo "wow", riesgo bajo (humano en el loop), y demo vendible en una landing.
- **Modelo**: clase Sonnet (calidad de redacción).
- **Éxito**: % de borradores usados/editados vs descartados; reducción del tiempo-a-primera-respuesta.

### 1B) Auto-triage al crear el ticket
- **Qué**: al crear un ticket, la IA sugiere **categoría, prioridad y agente/área** de asignación.
- **Dónde encaja**: hook de creación en `tickets_t` → `ai/` → setea prioridad (que alimenta `sla`) y sugiere asignación.
- **Por qué**: mejora el SLA automáticamente y ahorra el triage manual; barato y de alto volumen.
- **Modelo**: clase Haiku (clasificación, alto volumen, bajo costo).
- **Éxito**: precisión de categoría/prioridad vs corrección humana; impacto en cumplimiento de SLA.

---

## Fase 2 — Productividad y priorización inteligente

### 2A) Resumen de conversación
- **Qué**: resumen del hilo al reasignar/escalar un ticket largo ("ponete al día en 3 líneas").
- **Dónde**: `tickets_t` → `ai/`. Se guarda en el evento de reasignación (`TicketEvent`).
- **Modelo**: clase Sonnet. **Éxito**: uso en reasignaciones; tiempo de handoff.

### 2B) Análisis de sentimiento → prioridad/SLA
- **Qué**: detectar frustración/urgencia en los mensajes y **subir prioridad** o marcar riesgo de churn.
- **Dónde**: pipeline de mensajes → `ai/` → señal que alimenta `sla` y `notifications`.
- **Modelo**: clase Haiku. **Éxito**: tickets "rescatados" a tiempo; correlación con CSAT.

---

## Fase 3 — Self-service y deflección *(requiere base de conocimiento)*

### 3A) Base de conocimiento (prerequisito)
- **Qué**: modelo de KB por tenant (artículos), editable desde el admin (reusa el patrón de `landing_cms`).
- **Por qué**: sin KB no hay deflección; además es SEO y valor por sí sola.

### 3B) Agente IA de deflección (RAG sobre la KB)
- **Qué**: antes de crear ticket, un asistente responde con la KB de la org (retrieval + generación). Si no puede, escala a humano creando el ticket con contexto.
- **Dónde**: widget/portal del cliente → `ai/` + retrieval sobre la KB del tenant.
- **Por qué**: acá está el ROI real (bajar volumen de tickets).
- **Modelo**: clase Sonnet + retrieval. **Éxito**: **tasa de deflección** (consultas resueltas sin agente).

---

## Fase 4 — Inteligencia de negocio

- **Insights sobre CSAT/métricas**: la IA resume tendencias, detecta temas recurrentes y sugiere acciones sobre `csat` + `metrics`.
- **Auto-tagging y clustering de tickets**: agrupar por tema para ver "qué rompe más".
- **Éxito**: adopción del panel de insights; acciones tomadas.

---

## Preocupaciones transversales
| Tema | Cómo se maneja |
|---|---|
| **Privacidad multi-tenant** | Prompts/retrieval scoped por org; nunca cruzar datos entre tenants (respeta el aislamiento ya auditado) |
| **Costo** | Modelo barato para clasificar, caro para generar; presupuesto y rate-limit por org; prompt-caching |
| **Gating por plan** | IA como feature de Pro/Business en `billing` → palanca de monetización |
| **Confiabilidad** | Humano en el loop en Fase 1–2; guardrails y fallback sin IA |
| **Evaluación** | Set de eval + métrica de éxito por feature; no shippear sin medir |
| **Datos del cliente** | Opt-in explícito; política clara de qué se manda a la IA; redacción de secrets |

---

## Secuencia recomendada (primer milestone vendible)
1. **Fase 0** (gateway + config + guardrails). *Habilitador.*
2. **1A · Auto-borrador de respuesta.** ← el feature demo que ancla la landing y el pitch.
3. **1B · Auto-triage.** ← valor silencioso que mejora el SLA.
4. Recién ahí: Fase 2 (resumen + sentimiento), y en paralelo empezar la **KB** para habilitar la deflección (Fase 3, el de mayor ROI a mediano plazo).

**En una frase para la landing:** *"Tu equipo responde el doble de rápido: AllSafe redactará el borrador, priorizará el ticket y resumirá el hilo — vos solo revisás y enviás."*

---

## Estado (2026-07-28)
✅ Fase 0 (gateway) · ✅ Fase 1 (1A borrador + 1B triage) · ✅ Fase 2 (2A resumen + 2B sentimiento) · ✅ Fase 3 (3A KB + 3B deflección RAG) · ✅ Fase 4 (insights) · ✅ **Gateway multi-proveedor** (Claude/Gemini/OpenAI, elegible por despliegue).
✅ **Fase 5**: 5.1 omnicanal WhatsApp (#9) · 5.2 KB auto-alimentada (#10) · 5.3 multilingüe (#11) · 5.4 posicionamiento "IA sin lock-in".

---

## Fase 5 — Diferenciadores de mercado (post-wedge) — ✅ implementada
El wedge de IA está completo; estos cuatro son las apuestas para **destacar** en el
mercado LATAM/PyME. Orden de construcción recomendado (1→4):

### 5.1) Omnicanal donde están los clientes ⭐ (empezar acá)
- **Qué**: recibir/responder por los canales reales de LATAM. **WhatsApp** primero
  (Cloud API de Meta), luego **email-to-ticket** e **Instagram/Messenger DM**, y un
  **widget embebible** para la web del cliente.
- **Combo clave**: la deflección RAG (3B) corre sobre WhatsApp/widget → el bot
  responde con la KB y escala a humano solo si hace falta.
- **Arquitectura**: app `inbound` con abstracción de canal (ingesta por webhook →
  ticket + hilo por contacto → deflección → respuesta saliente). Las credenciales
  del canal (Meta, SMTP) son config de despliegue, igual que las keys de IA.
- **Éxito**: % de conversaciones iniciadas fuera del portal; deflección por canal.

### 5.2) KB que se auto-alimenta (flywheel)
- **Qué**: al resolver un ticket, la IA propone un artículo de KB a partir del hilo
  (borrador que el admin aprueba). La KB crece sola → mejor deflección → menos tickets.
- **Dónde**: hook al pasar a RESOLVED → `ai/` genera título+cuerpo → cola de
  "sugerencias de KB" en el admin. Cierra el loop 3A↔3B.
- **Modelo**: clase quality. **Éxito**: artículos publicados desde sugerencias;
  impacto en tasa de deflección.

### 5.3) Multilingüe real
- **Qué**: detectar el idioma del cliente; el agente escribe en español y la IA
  traduce ida y vuelta. Atender clientes en inglés/portugués sin equipo bilingüe.
- **Dónde**: pipeline de mensajes → `ai/` (detección + traducción). Se apoya en el
  gateway multi-proveedor existente.
- **Éxito**: conversaciones cross-idioma atendidas; CSAT en esos casos.

### 5.4) Posicionamiento "IA sin lock-in"
- **Qué**: hacer explícito en pricing/landing que el cliente elige Claude/Gemini/
  OpenAI y trae su propia key (ya construido en el gateway multi-proveedor).
  Transparencia + control de costos de IA = argumento de venta real vs incumbentes.
- **Esfuerzo**: casi nulo (copy + una sección en la landing/pricing).

### Moat de confianza (transversal a Fase 5)
- Cumplimiento y **residencia de datos** (LGPD Brasil, Ley 25.326 Argentina), log de
  auditoría, exportación/borrado por cliente. Apoyarse en la auditoría de seguridad
  ya hecha (cyber-neo).
- **Predicción de incumplimiento de SLA**: avisar *antes* de romper el SLA (sobre
  los datos de `sla`), no después.

### Integraciones table-stakes
Slack/Teams, Zapier/Make, webhooks salientes, PWA/app móvil para agentes.

---

## Fuera de este roadmap (pero clave para el wedge)
- **Email-to-ticket** e **integración de WhatsApp**: ahora incorporados como **Fase
  5.1 (omnicanal)**. Ver `.agents/product-marketing.md` (Differentiation y Gaps).
