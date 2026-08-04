# LinkedIn Post

## English

I am building JANUS because I want to spend less time coding and more time planning.

JANUS is a multi-agent harness for the MalariaSentinel repository. Above it sits the supervisor — the opencode primary agent that plans and integrates. Below it sits JANUS itself: one orchestrator with two entry modes that talk to each other. The onboarding REPL handles natural language in English or Spanish, runs the ABM and pipeline stages, and routes complex goals to the improvement orchestrator. The improvement orchestrator runs a seven-phase methodology, spawns eight specialized subagents from a registry, and reviews their patches through gitagent.

Each subagent — abm, scoring, ingest, download, prediction, training, data, commonlib — edits in its own isolated gitagent worktree. Their proposals flow through a mailbox, get validated by a plain-code scope checker, and converge into one clean commit on main.

Today this works. It is also still in development: full session replay, a clearer goal language, and stronger safety nets are pending.

This project is made possible by ANFAIA — Asociación Nacional Faro, para la Aceleración de la Inteligencia Artificial.

Feedback and collaboration welcome.

github.com/ANFAIA/MalariaSentinel

#MultiAgentSystems #AgenticAI #OpenSource #MalariaSentinel

---

## Versión en español

Estoy construyendo JANUS porque quiero dedicar menos tiempo a programar y más tiempo a planificar.

JANUS es un harness multiagente para el repositorio MalariaSentinel. Encima se sienta el supervisor — el agente principal de opencode que planifica e integra. Debajo se sienta JANUS: un orchestrator con dos modos de entrada que se hablan entre sí. El REPL de onboarding entiende lenguaje natural en español o inglés, ejecuta el ABM y las etapas del pipeline, y delega metas complejas al orchestrator de mejora. El orchestrator de mejora sigue una metodología de siete fases, lanza ocho subagentes especializados desde un registro y revisa sus parches a través de gitagent.

Cada subagente — abm, scoring, ingest, download, prediction, training, data, commonlib — edita dentro de su propio worktree aislado de gitagent. Sus propuestas pasan por un mailbox, las valida un verificador de scope en código plano, y confluyen en un único commit limpio sobre main.

Hoy funciona. También está en desarrollo: replay completo de sesiones, un lenguaje de objetivos más claro y mejores redes de seguridad siguen pendientes.

Este proyecto es posible gracias a ANFAIA — Asociación Nacional Faro, para la Aceleración de la Inteligencia Artificial.

Comentarios y colaboración son bienvenidos.

github.com/ANFAIA/MalariaSentinel

#SistemasMultiagente #IAAgéntica #OpenSource #MalariaSentinel
