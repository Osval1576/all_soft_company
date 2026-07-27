# Product Marketing Context

*Last updated: 2026-07-27*

> Nota: este documento es un **borrador de posicionamiento** derivado del código y del análisis competitivo, no de entrevistas a clientes reales. Las secciones de personas / lenguaje del cliente son **hipótesis a validar** con usuarios reales, no citas verbatim.

## Product Overview
**One-liner:** Mesa de ayuda con IA, en español, para PyMES y agencias de LATAM — con white-label de fábrica.
**What it does:** AllSafe es una plataforma multi-tenant de soporte al cliente: tickets, chat en tiempo real, SLA, encuestas de satisfacción (CSAT), métricas y facturación. Cada organización puede personalizar marca (logo, color, dominio de login) y operar de forma aislada. El diferenciador buscado es ser **AI-native y español-first** frente a incumbentes caros y en inglés.
**Product category:** Help desk / customer support software (mesa de ayuda / soporte al cliente).
**Product type:** SaaS B2B multi-tenant (con capa white-label para revendedores).
**Business model:** Suscripción por planes (Free/Pro/Business) vía Stripe, con trials y límite de agentes por plan.

## Target Audience
**Target companies:** PyMES latinoamericanas (5–200 empleados) que dan soporte a clientes; y **agencias/MSPs** que quieren revender soporte bajo su marca.
**Decision-makers:** dueño/gerente de PyME, líder de soporte/atención al cliente, o el fundador de la agencia/MSP.
**Primary use case:** centralizar y profesionalizar la atención al cliente (hoy dispersa en WhatsApp/email/planillas) con SLA, métricas y una marca propia.
**Jobs to be done:**
- "Ayudame a no perder mensajes de clientes y responder a tiempo" (SLA/organización).
- "Dame visibilidad de cómo va mi soporte" (métricas/CSAT).
- "Dejame ofrecer soporte con MI marca a mis clientes" (white-label, agencias/MSPs).
**Use cases:**
- Equipo de soporte de una PyME gestionando tickets con SLA y satisfacción.
- Agencia/MSP operando la mesa de ayuda de varios clientes bajo su propia marca.
- Onboarding de un cliente nuevo por invitación con login branded (`/o/:slug/login`).

## Personas
| Persona | Cares about | Challenge | Value we promise |
|---------|-------------|-----------|------------------|
| Líder de soporte (usuario/champion) | No perder tickets, cumplir SLA, ver métricas | Herramientas caras/en inglés o el caos de WhatsApp+Excel | Orden, SLA y métricas en español, con IA que ahorra tiempo |
| Dueño de PyME (decision/financial) | Costo, simplicidad, imagen profesional | Zendesk es caro y sobredimensionado | Precio local, setup rápido, marca propia |
| Fundador de agencia/MSP (decision) | Revender soporte con su marca, márgenes | White-label solo en planes enterprise carísimos | White-label de fábrica + multi-tenant + billing |
| Agente/técnico (usuario) | Responder rápido y bien | Contexto disperso, respuestas repetitivas | IA que redacta borradores y resume el hilo |

## Problems & Pain Points
**Core problem:** las PyMES de LATAM atienden clientes en canales dispersos (WhatsApp, email, DMs) sin SLA, sin métricas y sin marca profesional; los helpdesks serios son caros, en inglés y sobredimensionados.
**Why alternatives fall short:**
- Zendesk/Intercom: caros (USD/agente), en inglés, curva de setup, WhatsApp como add-on caro.
- WhatsApp/Excel/email: cero SLA, cero métricas, se pierden mensajes, no escala.
- Open-source (Chatwoot): potente pero requiere self-host/DevOps y no es AI-native ni pensado para el no-técnico.
**What it costs them:** clientes perdidos por respuestas tardías, horas del equipo en tareas repetitivas, cero data para mejorar.
**Emotional tension:** miedo a quedar mal frente al cliente, sensación de caos, "esto no escala".

## Competitive Landscape
**Direct:** Zendesk, Freshdesk, Zoho Desk, Intercom, Help Scout, Gorgias — completos pero caros, English-first y con IA atornillada sobre arquitecturas viejas.
**Secondary (open-source / low-cost):** Chatwoot, FreeScout, Crisp, Tidio — buenos en precio pero self-host/DevOps o features limitados; no AI-native.
**Indirect:** WhatsApp Business + planillas + email compartido — el "status quo" de la PyME latinoamericana; gratis pero sin SLA/métricas/escala.

## Differentiation
**Key differentiators:**
- **AI-native desde el modelo de datos** (no un add-on): auto-triage, borradores de respuesta, resúmenes, deflección.
- **Español-first + LATAM**: idioma, precio local, y (roadmap) **WhatsApp como canal nativo**.
- **White-label de fábrica**: branding por tenant + multi-tenant + billing → ideal para agencias/MSPs.
- Base moderna y segura: real-time (WebSockets), motor de SLA, CSAT, métricas, auditado (OWASP/CWE).
**How we do it differently:** en vez de competir por paridad de features contra gigantes, clavamos un wedge (IA + español + white-label) donde son caros/lentos/en inglés.
**Why that's better:** el equipo responde más rápido y mejor (IA), a un precio y en un idioma que les cierra, con su propia marca.
**Why customers choose us:** "el helpdesk con IA hecho para nosotros (LATAM), no una traducción cara de una herramienta gringa".

## Objections
| Objection | Response |
|-----------|----------|
| "¿Por qué no Zendesk?" | Zendesk es caro, en inglés y sobredimensionado para una PyME; AllSafe es español-first, con IA incluida y precio local |
| "¿La IA es confiable?" | La IA asiste (borradores/triage), el agente siempre decide; con guardrails y opt-in por org |
| "¿Mis datos están seguros / aislados?" | Multi-tenant con aislamiento verificado + auditoría de seguridad (OWASP/CWE) |
| "Ya uso WhatsApp" | Justamente: (roadmap) integramos WhatsApp como canal de tickets, sumando SLA y métricas que WhatsApp no da |

**Anti-persona:** enterprise grande con necesidades de compliance pesado (SOC2/on-prem) y decenas de integraciones — hoy no es el fit; el fit es PyME/agencia ágil.

## Switching Dynamics
**Push:** herramienta cara/en inglés, o el caos de WhatsApp+Excel; se pierden mensajes.
**Pull:** IA que ahorra tiempo, español, precio local, marca propia.
**Habit:** "ya estamos acostumbrados a WhatsApp"; migrar da pereza.
**Anxiety:** "¿migrar es un lío?", "¿la IA responde cualquier cosa?", "¿y si es otra herramienta que no uso?".

## Customer Language
*(hipótesis a validar con usuarios reales)*
**How they describe the problem:**
- "Se me pierden los mensajes de los clientes."
- "No tengo idea de cuánto tardamos en responder."
- "Zendesk es un montón para lo que necesito."
**How they describe us:**
- "Es como Zendesk pero en español y con IA, y me sale bien de precio."
**Words to use:** mesa de ayuda, soporte, tickets, SLA, en español, tu marca, con IA, WhatsApp.
**Words to avoid:** jerga enterprise ("ITSM", "omnichannel orchestration"), términos que suenen caros/complejos.
**Glossary:**
| Term | Meaning |
|------|---------|
| Tenant / organización | Cada empresa cliente, aislada |
| White-label | Operar con la marca del cliente/agencia |
| SLA | Compromiso de tiempo de respuesta/resolución |
| CSAT | Encuesta de satisfacción post-ticket |
| Deflección | Resolver sin agente (self-service/IA) |

## Brand Voice
**Tone:** cercano, directo, práctico — sin corporativismo.
**Style:** conversacional y claro, español rioplatense/neutro; explica sin jerga.
**Personality:** confiable, moderno, ágil, honesto, con IA "que ayuda, no que reemplaza".

## Proof Points
**Metrics (técnicas, hoy):** multi-tenant aislado y auditado (OWASP/CWE); ~290 tests de backend en verde; real-time verificado; billing Stripe funcionando.
**Customers:** ninguno aún (pre-lanzamiento) — *pendiente conseguir 3–5 pilotos*.
**Testimonials:** *pendiente*.
**Value themes:**
| Theme | Proof |
|-------|-------|
| AI-native | (roadmap) auto-triage/draft/resumen sobre el propio modelo de datos |
| Español + LATAM | producto íntegramente en español; (roadmap) WhatsApp |
| White-label | branding por tenant + multi-tenant + billing ya funcionando |
| Base sólida/segura | auditoría de seguridad + suite de tests + real-time |

## Goals
**Business goal:** validar el wedge (IA + español + white-label) con 3–5 pilotos de PyME/agencia LATAM.
**Conversion action:** alta a trial (registro de empresa) → activar org branded.
**Current metrics:** pre-lanzamiento (sin usuarios reales todavía).
