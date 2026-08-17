# Janus + GAWT: plan integral de tools, MCP, identidad y colisiones

Estado: implementacion inicial completada; endurecimiento pendiente
Fecha: 2026-08-17
Repositorios implicados:

- Janus: `agents/janus/`
- GAWT: `/Users/davidflorezmazuera/Library/CloudStorage/SynologyDrive-DFM/Desarrollos/gitagent`

## 1. Resumen ejecutivo

Janus tiene actualmente demasiada logica distribuida entre codigo, prompts y
middlewares para decidir que puede hacer cada agente. GAWT expone correctamente
operaciones de sesiones, agentes, intents, ediciones, inbox y conflictos, pero
su contrato MCP actual requiere mejoras para integracion robusta.

Direccion propuesta:

```text
config declarativa
  -> Pydantic estricto
  -> descubrir MCPs y tools
  -> aplicar allowlist por agente
  -> construir coordinator/specialists
  -> adaptador pequeno de identidad GAWT
  -> GAWT valida operaciones y estado
```

Principios:

- Configuracion decide superficie de tools.
- DeepAgents recibe solo tools autorizadas.
- Middleware no sustituye configuracion.
- GAWT sigue siendo propietario de Git, SQLite, sesiones e integridad.
- Janus sigue siendo propietario de planificacion, delegacion y decision.
- `MCP session` no se usa como identidad de specialist.
- `GAWT agent_id` es identidad de aplicacion, no identidad MCP.
- Estado persistente se pasa explicitamente o se inyecta fuera del modelo.
- Primero se estabiliza contrato y seguridad; despues se optimiza experiencia.

Implementacion inicial ejecutada sobre Janus y GAWT. Este documento sigue
siendo referencia para fases pendientes y validacion de integracion real.

## 2. Estado actual

### 2.1. Janus

Janus usa `create_deep_agent()` y dispone de estos modos:

- `request_router`;
- `research_coordinator`;
- `implementation_coordinator`.

Configuracion existente:

- `src/agents_janus/config/janus.json`: servidores MCP y prefijos;
- `src/agents_janus/config/subagents.yaml`: especialistas, roles, skills y scopes;
- `src/agents_janus/mcp_config_schema.py`: modelos Pydantic para servidores MCP;
- `src/agents_janus/mcp_bridge.py`: discovery y conversion MCP -> LangChain tools;
- `src/agents_janus/agent.py`: construccion de agents y subagents;
- `src/agents_janus/middleware/`: filtros, identidad, inbox, observabilidad y lifecycle.

Servidores configurados:

- `gitagent` por `stdio`;
- `codebase_memory` por `stdio`.

Capacidades confirmadas en Janus:

- carga de herramientas MCP;
- separacion parcial entre GAWT y codebase memory;
- tools diferentes por specialist;
- middleware LangGraph;
- prompts distintos por coordinator y specialist;
- checkpointer para graph;
- prefijos de nombres MCP.

Problemas actuales:

- `janus.json` declara servidores, pero no superficie por agente;
- `subagents.yaml` declara scopes, pero no tools MCP autorizadas;
- `agent.py` pasa inicialmente demasiadas tools al implementation coordinator;
- `ToolFilterMiddleware` intenta corregirlo despues;
- filtro puede no cubrir nombres MCP prefijados;
- `gawt_role` y nombre interno no se propagan siempre igual;
- `ScopeValidationMiddleware` es advisory, no bloqueo;
- `InboxCheckMiddleware` detecta despues de ejecutar tool;
- registro de identidad usa un transporte diferente al bridge MCP;
- bridge declara HTTP, pero solo implementa stdio;
- configuracion invalida puede degradar a cero MCP en vez de fallar pronto.

### 2.2. GAWT

GAWT expone MCP por `stdio` desde:

```text
src/gitagent/mcp_server.py
```

Tools actuales:

- lifecycle: `start_session`, `get_session`, `finalize_session`, `abort_session`;
- agentes: `register_agent`, `unregister_agent`, `list_agents`;
- intents: `start_intent`, `repurpose`, `get_current_intent`;
- archivos: `read_file`, `edit_file`, `write_file`, `delete_file`;
- coordinacion: `check_inbox`, `send_message`;
- observabilidad: `list_edits`, `list_intents`.

Las tools mutantes reciben `agent_id` explicitamente. Eso es correcto para
GAWT actual: el MCP no conoce automaticamente que specialist origino una call.

Problemas confirmados:

- resultados devuelven `str(dict)` o `str(list)` en vez de datos estructurados;
- errores devuelven texto `error: ...` como resultado normal;
- `Mcp-Session-Id` no representa specialist;
- `stdio` no ofrece identidad de agente por protocolo;
- agentes pueden competir por session global;
- lifecycle carece de locking de dominio suficiente;
- deteccion de conflictos es advisory y posterior a escritura;
- inbox no hace claim/ack atomico;
- containment de paths usa `startswith()`;
- `finalize_session` puede incluir todos los cambios del worktree.

### 2.3. Evidencia de trace

Trace revisada:

```text
0feb1ff0cab1dc2d6e8a26e031ca8eff
```

Hechos observados:

- `start_session` fallo con `target_branch=None`;
- retry recibio `Session already open`;
- specialist uso paths incorrectos y gasto ciclos descubriendo worktree;
- coordinator produjo llamadas de filesystem que no deberia recibir;
- hubo trabajo parcial sin `finalize_session`;
- no hubo cleanup completo de agentes.

Diagnostico:

```text
tool surface no es declarativa ni estricta
identidad GAWT no esta integrada de forma uniforme
MCP transport session no equivale a agent identity
GAWT contrato MCP devuelve errores dificiles de interpretar
lifecycle y conflictos necesitan enforcement server-side
```

## 3. Modelo conceptual objetivo

### 3.1. Tres conceptos separados

```text
MCP transport/session
  = canal tecnico entre cliente y servidor

GAWT agent_id o agent_handle
  = identidad de aplicacion validada por GAWT

LangGraph/DeepAgents specialist
  = entidad de planificacion y ejecucion dentro de Janus
```

No se debe usar `Mcp-Session-Id` como `agent_id`.

Motivos:

- MCP legacy session identifica cliente/conexion, no specialist;
- varios specialists pueden multiplexar misma conexion;
- stdio no tiene session ID estandar;
- MCP actual es stateless y no debe inferir estado de conexiones previas;
- `_meta.clientInfo` es identificacion declarativa, no autenticacion.

### 3.2. Identidad GAWT

Primera implementacion:

```text
specialist
  -> llama tool sin conocer agent_id
  -> adaptador Janus inyecta agent_id en argumentos GAWT
  -> MCP transport
  -> GAWT valida agent_id, session y permisos
```

El modelo no debe manipular `agent_id` directamente.

Posible evolucion:

```text
register_agent
  -> devuelve agent_handle
  -> adapter mantiene handle en runtime/checkpoint
  -> GAWT valida (handle, session, permisos) en cada call
```

El handle sigue siendo estado de aplicacion explicito. No depende de session
MCP ni de "ultimo agente registrado".

## 4. Configuracion declarativa objetivo

### 4.1. Fuente unica

Crear:

```text
agents/janus/src/agents_janus/config/agents.yaml
```

Este archivo sustituira gradualmente la responsabilidad repartida entre:

- `janus.json`;
- `subagents.yaml`;
- constantes de filtros en Python;
- listas implicitas de tools en `agent.py`.

Durante migracion puede mantenerse compatibilidad temporal, pero no habra dos
fuentes activas para la misma decision.

### 4.2. Esquema conceptual

```yaml
version: 1

defaults:
  tool_name_prefix: true
  default_deny: true
  fail_on_missing_tools: true
  global_deny_tools:
    - "*delete*"
    - "*execute*"

servers:
  gitagent:
    transport: stdio
    command: uv
    args: [run, gitagent-mcp]
    cwd: <repo_root>

  codebase_memory:
    transport: stdio
    command: /Users/davidflorezmazuera/.local/bin/codebase-memory-mcp
    args: []
    cwd: <repo_root>

agents:
  implementation_coordinator:
    kind: coordinator
    servers: [gitagent, codebase_memory]
    tools:
      - mcp__gitagent__start_session
      - mcp__gitagent__get_session
      - mcp__gitagent__list_agents
      - mcp__gitagent__list_edits
      - mcp__gitagent__list_intents
      - mcp__gitagent__check_inbox

  abm:
    kind: specialist
    gawt_role: abm
    servers: [gitagent, codebase_memory]
    tools:
      - mcp__gitagent__read_file
      - mcp__gitagent__edit_file
      - mcp__gitagent__write_file
      - codebase_search_graph
      - execute
```

### 4.3. Reglas de resolucion

Orden:

```text
config global
  -> servidor
  -> tipo de agente
  -> nombre concreto
  -> tool final
```

Reglas:

- `servers` limita servidores disponibles;
- `tools` define superficie final visible;
- default deny;
- deny siempre gana sobre allow;
- nombres MCP prefijados son canonicos;
- wildcard solo se permite dentro de servidor y con deny explicito;
- tool ausente en discovery produce error de startup;
- schema cambiado produce warning o error en modo estricto;
- specialist no recibe tools de delegacion salvo declaracion expresa;
- coordinator no recibe filesystem por defecto;
- lifecycle GAWT solo se asigna a coordinator;
- `finalize_session` y `abort_session` requieren policy explicita.

### 4.4. Modelo Pydantic

Implementar modelos con:

- `extra="forbid"`;
- enums para transport y kind;
- validacion de referencias a servers;
- validacion de `stdio` frente a `http`;
- validacion de nombres unicos;
- validacion de tools declaradas contra catalogo descubierto;
- validacion de que no se asigna lifecycle sensible a specialist;
- validacion de que no se asigna `execute` sin policy especial.

La carga debe fallar pronto. No devolver configuracion vacia silenciosamente.

### 4.5. Server catalog y discovery

Flujo:

```text
load agents.yaml
  -> validar estructura
  -> conectar servers habilitados
  -> tools/list
  -> normalizar nombres y prefijos
  -> aplicar allow/deny
  -> validar tools requeridas
  -> construir agent definitions
```

El catalogo debe registrar fingerprint de:

- servidor;
- transporte;
- command/URL sin secretos;
- nombres de tools;
- schemas de entrada.

Si MCP anuncia `tools/list_changed`:

- no otorgar permisos nuevos automaticamente;
- volver a aplicar allowlist;
- comparar fingerprint;
- bloquear tool autorizada si schema cambio de forma incompatible;
- registrar evento de cambio.

## 5. Integracion Janus con LangGraph/DeepAgents

### 5.1. No crear middleware para cargar MCP

Usar adaptador MCP estandar o bridge actual simplificado.

Responsabilidades de carga:

- `MultiServerMCPClient` o equivalente;
- discovery;
- prefijos;
- conversion a LangChain tools;
- resolucion declarativa.

Middleware queda reservado para runtime:

- identidad GAWT;
- auditoria;
- bloqueo de llamada;
- transformacion de argumentos;
- inbox;
- lifecycle.

### 5.2. Construccion de coordinator

`create_deep_agent()` recibe solo tools resueltas para coordinator.

No se debe hacer:

```python
orch_tools = all_gawt_tools
ToolFilterMiddleware(...)
```

Se debe hacer:

```python
orch_tools = resolve_tools(config, "implementation_coordinator")
```

El middleware de filtro queda como defensa secundaria, no como mecanismo
principal de autorizacion.

### 5.3. Construccion de specialists

Cada specialist se crea con:

- nombre DeepAgents;
- descripcion;
- system prompt;
- tools finales desde config;
- modelo/proveedor desde config o defaults;
- skills desde config;
- `gawt_role` canonico;
- middleware declarado o defaults seguros;
- scope de paths.

No duplicar listas de tools en prompt.

### 5.4. Adaptador GAWT en Janus

Crear una capa pequena, por ejemplo:

```text
middleware/gawt_context.py
```

Responsabilidades:

- registrar specialist al inicio;
- guardar `agent_id` en runtime/checkpoint;
- reutilizarlo solo despues de validarlo;
- inyectarlo en tools que lo requieren;
- usar `from_agent_id` para `send_message`;
- impedir que specialist use tools de lifecycle;
- desregistrar al terminar;
- informar error estructurado al graph.

No debe:

- manipular SQLite;
- manipular Git;
- resolver merge semantico;
- decidir permisos fuera de config;
- usar import directo de `gitagent.mcp_server` si MCP es el transporte elegido.

## 6. Plan de modificacion Janus

### J1. Definir contrato de configuracion

Archivos:

- nuevo `config/agents.yaml`;
- `mcp_config_schema.py`;
- `subagents/base.py`;
- `subagents/registry.py`.

Trabajo:

- crear modelos Pydantic;
- incorporar servers, agents, tools, roles y middleware;
- mantener `subagents.yaml` solo durante migracion;
- detectar referencias desconocidas;
- eliminar defaults silenciosos.

Salida:

- catalogo valido cargado en memoria;
- tests de schema y errores de configuracion.

### J2. Crear resolver de tools

Archivos:

- nuevo `tool_catalog.py` o modulo equivalente;
- `mcp_bridge.py`;
- tests de catalogo.

Trabajo:

- conectar MCPs declarados;
- descubrir tools;
- normalizar prefijos;
- resolver por agent;
- aplicar deny global y local;
- fallar si falta tool requerida;
- devolver tools LangChain finales.

Salida:

- cada agent recibe lista exacta;
- coordinator no recibe filesystem por accidente;
- nombres prefijados cubiertos por tests.

### J3. Sustituir filtros implicitos

Archivos:

- `agent.py`;
- `middleware/tool_filter.py`;
- tests de construccion.

Trabajo:

- retirar `all_gawt_tools` del coordinator;
- usar resolver declarativo;
- conservar filtro como defensa secundaria;
- eliminar constantes duplicadas cuando config las sustituya;
- comprobar exposicion real del graph construido.

Salida:

- test confirma ausencia de `write_file`, `read_file`, `execute` en coordinator;
- test confirma herramientas esperadas en cada specialist.

### J4. Unificar identidad

Archivos:

- `middleware/agent_identity.py`;
- nuevo `middleware/gawt_context.py` si se separan responsabilidades;
- `middleware/inbox_check.py`;
- `agent.py`;
- tests.

Trabajo:

- usar transporte MCP unico;
- pasar `gawt_role`, no nombre YAML accidental;
- guardar identidad en runtime/checkpoint;
- validar identidad antes de reutilizarla;
- inyectar argumentos solo en tools GAWT mutantes;
- ocultar `agent_id` al modelo.

Salida:

- mismo agent_id en register, intent, edit, inbox y unregister;
- recovery no usa ID obsoleto;
- no existe import directo alternativo.

### J5. Normalizar paths

Archivos:

- `mcp_bridge.py`;
- `scope_validator.py`;
- prompts;
- tests.

Trabajo:

- contrato unico: path relativo al worktree;
- normalizar antes de comparar scope;
- rechazar path externo;
- documentar root GAWT para specialist;
- no exponer path interno `.gitagent/worktree` al modelo.

Salida:

- specialist recibe root relativo claro;
- no gasta ciclos descubriendo path;
- paths fuera de worktree fallan antes de modificar.

### J6. Lifecycle en Janus

Archivos:

- `consensus_guard.py`;
- `improvement.py`;
- prompts;
- tests.

Trabajo:

- estados explicitos;
- error no cambia estado a exito;
- retry consulta session existente;
- task requiere session confirmada;
- finalize requiere tasks terminadas y verificacion;
- excepcion intenta abort;
- cleanup en `finally`.

Salida:

- no retry ciego de `start_session`;
- toda ejecucion termina con finalize o abort;
- estado Janus coincide con respuesta GAWT.

### J7. Inbox y conflicto en runtime

Archivos:

- `inbox_check.py`;
- `scope_validator.py`;
- `resolve_conflict.py`;
- tests.

Trabajo:

- conflicto estructurado;
- bloquear siguientes ediciones del specialist afectado;
- conservar mensaje original;
- exigir decision de `resolve_conflict`;
- reactivar edicion solo despues de decision;
- limitar retries sin progreso.

Limite:

La primera escritura concurrente solo puede prevenirse completamente desde
GAWT. Janus puede detener la siguiente llamada, no deshacer atomically la
primera escritura.

## 7. Limpieza previa obligatoria

Esta fase ocurre antes de implementar configuracion nueva, resolver de tools,
middleware nuevo o cambios de identidad. No se construye encima del estado
actual ambiguo.

Objetivo:

```text
inventariar
  -> clasificar
  -> eliminar legacy y trabajo abandonado
  -> comprobar imports rotos esperados
  -> reconstruir desde contrato nuevo
```

### 7.1. Regla de limpieza

Todo archivo, clase, funcion, tool, middleware, prompt o configuracion debe
quedar en una de estas categorias:

- conservar: necesario para arquitectura nueva;
- migrar: contiene logica util que se reescribira en destino nuevo;
- eliminar: legacy, duplicado, experimento abandonado o camino no usado;
- revisar: dependencia no confirmada, requiere decision antes de borrar.

No se conservara codigo solo porque exista importado por otro codigo legacy.
Un import legacy es evidencia para inventario, no razon para mantenerlo.

No se añadiran aliases, shims ni wrappers de compatibilidad salvo necesidad
demostrada por un consumidor externo persistente.

### 7.2. Inventario previo

Antes de borrar:

- capturar `git status` y diff existente;
- identificar entrypoints CLI reales;
- identificar factory real de Janus;
- identificar tests que representan comportamiento objetivo;
- listar imports de cada middleware, tool, prompt y config;
- buscar referencias textuales y simbolicas;
- registrar archivos sin referencias;
- separar cambios del usuario de cambios de esta tarea;
- guardar inventario en documento o artefacto revisable.

El inventario debe cubrir como minimo:

- `agent.py`;
- `mcp_bridge.py`;
- `mcp_config_schema.py`;
- `config/janus.json`;
- `config/subagents.yaml`;
- `subagents/`;
- `middleware/`;
- `tools/`;
- `prompts/`;
- `scope_validator.py`;
- `improvement.py`;
- tests Janus;
- imports desde CLI, onboarding y observabilidad.

### 7.3. Baseline de comportamiento

Antes de eliminar:

- ejecutar tests actuales y guardar resultado;
- ejecutar import smoke tests;
- construir cada modo de orchestrator existente;
- capturar lista efectiva de tools por modo;
- capturar prompts realmente renderizados;
- capturar middleware realmente instalado;
- guardar trace o logs suficientes para distinguir comportamiento usado de
  comportamiento declarado pero muerto.

El baseline no define arquitectura futura. Solo evita borrar por desconocimiento.

### 7.4. Elementos candidatos a eliminar

Se eliminaran despues de confirmar referencias:

- middleware que duplique autorizacion declarativa;
- middleware creado para compensar tool exposure incorrecta;
- middleware de identidad antiguo si se sustituye por adaptador unico;
- middleware de inbox que dependa de transporte paralelo al MCP bridge;
- guards de lifecycle que queden sustituidos por estado claro y GAWT server-side;
- tools locales que dupliquen tools MCP;
- wrappers antiguos de GitAgent/GAWT;
- funciones no llamadas por entrypoints objetivos;
- constantes de allow/deny que pasen a `agents.yaml`;
- config duplicada entre `janus.json` y `subagents.yaml`;
- campos de config no consumidos;
- builders o registries que queden sustituidos por resolver unico;
- prompts especificos de modos eliminados;
- tests de protocolo antiguo que validen comportamiento que ya no existira;
- documentos o ejemplos que describan flujo eliminado, cuando no sean
  referencia historica necesaria.

No se borraran automaticamente:

- prompts de dominio aun usados por specialists;
- observabilidad activa;
- checkpointer requerido por `resolve_conflict` u operaciones de graph;
- tools de usuario necesarias para CLI;
- codigo GAWT del repositorio externo sin plan y confirmacion separados.

### 7.5. Limpieza de middleware

La meta no es mantener una cadena larga de middleware que replique policy.

Despues de limpieza debe quedar, como maximo:

- middleware de observabilidad;
- adaptador de contexto GAWT;
- middleware de bloqueo runtime estrictamente necesario;
- middleware de aprobacion humana, si existe requisito real.

Debe eliminarse o fusionarse cualquier middleware que solo:

- oculte tools que nunca debieron entrar al graph;
- repita registro/desregistro ya gestionado por adaptador;
- convierta errores de strings sin contrato;
- mantenga estado duplicado de session;
- implemente scope que GAWT debe imponer;
- haga polling redundante cuando GAWT tenga inbox tipado.

### 7.6. Limpieza de tools y archivos

La superficie final no se obtendra deshabilitando tools antiguas. Se borraran
las implementaciones y wrappers que no pertenezcan al modelo nuevo.

Procedimiento:

1. Enumerar tools locales y tools MCP.
2. Marcar duplicados por capacidad.
3. Elegir una fuente canonica.
4. Eliminar wrapper no canonico.
5. Eliminar imports y tests exclusivos del wrapper.
6. Eliminar archivos vacios o modulos sin consumidores.
7. Verificar que referencias restantes fallan de manera explicita.

Regla:

```text
config decide que tool entra
MCP implementa capacidad externa
Janus no mantiene copia local de capacidad GAWT
```

### 7.7. Limpieza de prompts

Los prompts no se borraran por defecto. Se conservaran solo si describen
responsabilidad del agente despues de la limpieza.

Eliminar o reescribir:

- instrucciones de registro manual si identity lo hace el adaptador;
- instrucciones que asignan tools no recibidas;
- protocolos de session antiguos;
- nombres de tools retiradas;
- instrucciones duplicadas entre prompt y middleware;
- prompts de modos que desaparezcan.

Mantener:

- contexto de dominio;
- criterios de salida;
- formato de evidencia;
- reglas de comunicacion que el modelo debe ejecutar;
- instrucciones de decision ante conflicto.

### 7.8. Borrado y fallo intencional

Despues de limpieza, Janus debe fallar al importar o construir partes que aun
no hayan sido reconstruidas. Esto es intencional.

Se aceptan fallos como:

- `ModuleNotFoundError` de modulo eliminado;
- `ImportError` de simbolo retirado;
- config ausente o incompatible;
- factory incompleta;
- tests que referencien API eliminada.

No se arreglaran esos fallos creando aliases temporales. Se usaran como lista
de trabajo de reconstruccion.

Registrar:

- fallo exacto;
- archivo y simbolo faltante;
- reemplazo previsto;
- fase donde se reconstruira;
- si el fallo es esperado o inesperado.

### 7.9. Criterio de salida de limpieza

Limpieza termina cuando:

- inventario esta cerrado;
- cada elemento tiene categoria;
- archivos legacy fueron eliminados;
- no quedan wrappers duplicados sin justificacion;
- no quedan imports ocultos a codigo retirado salvo fallos documentados;
- baseline anterior esta guardado;
- fallos post-limpieza estan enumerados;
- estructura destino esta definida;
- `git diff` contiene solo limpieza y documentacion aprobadas.

No se considera exito que tests pasen en esta fase. El resultado esperado es
un repositorio limpio con fallos de reconstruccion conocidos.

## 8. Plan separado de modificacion GAWT

Repositorio:

```text
/Users/davidflorezmazuera/Library/CloudStorage/SynologyDrive-DFM/Desarrollos/gitagent
```

Este trabajo debe vivir en plan y cambios separados. GAWT no debe depender de
LangGraph ni DeepAgents.

### G1. Contrato MCP estructurado, prioridad P0

Archivos probables:

- `src/gitagent/mcp_server.py`;
- modelos de resultado nuevos;
- tests MCP nuevos.

Trabajo:

- devolver dict/list nativos;
- definir output schemas donde SDK lo permita;
- distinguir resultado exitoso de error;
- convertir `GitAgentError` a error MCP estructurado;
- incluir codigo estable:
  - `NO_SESSION`;
  - `INVALID_AGENT`;
  - `INVALID_PATH`;
  - `CONFLICT`;
  - `STALE_WRITE`;
  - `SESSION_ALREADY_OPEN`;
  - `SESSION_FINALIZED`.

Motivo:

Janus necesita saber si operation fallo sin parsear strings.

### G2. Seguridad de paths, prioridad P0

Archivos:

- `src/gitagent/edits.py`;
- tests de seguridad.

Trabajo:

- reemplazar `startswith()` por containment por componentes;
- resolver symlinks segun policy;
- rechazar escapes del worktree;
- normalizar paths relativos;
- validar que path no es worktree externo.

Motivo:

Prefijo textual no garantiza containment real.

### G3. Lifecycle atomico, prioridad P0

Archivos:

- `src/gitagent/session.py`;
- `src/gitagent/db.py`;
- `src/gitagent/mcp_server.py`;
- tests concurrentes.

Trabajo:

- lock de session global;
- transaccion check-then-create;
- constraint o garantia de una session abierta;
- lock de finalize/abort;
- validar branch sin interpolacion peligrosa;
- respuesta idempotente para retry seguro;
- bloquear finalize con agents activos, o policy explicita.

Motivo:

Dos procesos pueden observar ausencia de session y crear worktrees en carrera.

### G4. Identidad y autorizacion, prioridad P1

Trabajo base:

- mantener `agent_id` explicito como compatibilidad;
- validar agent en toda operation mutante;
- validar pertenencia a session;
- impedir finalize/abort desde specialist no autorizado;
- separar identidad de role y autorizacion.

Evolucion opcional:

- `register_or_get_agent(role, session_id)`;
- `agent_handle` opaco con expiracion;
- adapter MCP que resuelva handle a agent;
- soporte de contexto de conexion solo como optimizacion, no como fuente unica.

No hacer:

- guardar "ultimo agent registrado" por conexion compartida;
- quitar `agent_id` sin sustituirlo por handle/auth;
- confiar en `_meta.clientInfo` para seguridad.

### G5. Conflictos reales, prioridad P1

Archivos:

- `src/gitagent/edits.py`;
- `src/gitagent/db.py`;
- inbox y tests.

Trabajo:

- devolver hash base en lectura;
- aceptar expected hash en edit/write;
- rechazar stale write;
- registrar base hash y nuevo hash;
- deduplicar conflicto dentro de ventana;
- opcional lock por archivo;
- incluir conflicto en respuesta de edit, no solo inbox.

Objetivo:

Pasar de deteccion advisory posterior a rechazo verificable de sobrescritura.

### G6. Inbox atomico, prioridad P1

Trabajo:

- ID de mensaje;
- claim/ack individual;
- lectura atomica con marcado;
- cursor o timestamp seguro;
- no perder mensajes por dos consumidores concurrentes;
- tipos de mensaje definidos.

### G7. Transporte adicional, prioridad P2

Solo si se necesita uso remoto:

- Streamable HTTP;
- autenticacion OAuth/JWT;
- identidad por principal autenticado;
- scopes por role;
- timeouts y rate limits;
- no usar HTTP session como identidad de specialist.

## 9. Contrato de responsabilidades

### GAWT posee

- Git y worktree;
- SQLite y transacciones;
- session global;
- agentes y autorizacion;
- intents persistentes;
- lectura/escritura atomica;
- hashes y conflictos;
- inbox;
- finalize/abort;
- auditoria.

### Janus posee

- configuracion declarativa;
- discovery y seleccion de tools;
- prompts;
- planificacion;
- delegacion;
- scheduling;
- retries de tareas;
- estado de graph;
- decisiones ante conflicto;
- HITL;
- observabilidad Langfuse.

### MCP posee

- transporte;
- serializacion;
- discovery;
- contrato de tools;
- metadata protocol;
- auth de transporte cuando aplique.

MCP no decide que specialist tiene permiso. Janus resuelve superficie y GAWT
debe reforzar autorizacion para operaciones sensibles.

## 10. Tests y validacion

### Janus unit tests

- schema valida config completa;
- schema rechaza keys desconocidas;
- schema rechaza servers inexistentes;
- schema rechaza tools inexistentes;
- schema rechaza lifecycle a specialist;
- resolver aplica prefijos;
- resolver aplica default deny;
- deny gana sobre allow;
- coordinator recibe solo allowlist;
- specialists reciben tools declaradas;
- `gawt_role` llega a identity y observabilidad;
- identidad inyecta agent_id;
- identidad reemplaza checkpoint invalido;
- identity/inbox comparten agent_id;
- paths se comparan relativos;
- paths externos se bloquean;
- lifecycle no avanza tras error;
- cleanup ejecuta abort en excepcion;
- conflicto bloquea siguiente edicion;
- retry cambia argumentos o se detiene.

### GAWT unit tests

- output MCP es JSON estructurado;
- error MCP tiene codigo estable;
- path similar al worktree pero externo se rechaza;
- symlink escape se rechaza;
- dos `start_session` concurrentes dejan una sola session;
- finalize concurrente es seguro;
- agent de otra session no puede editar;
- specialist no puede finalizar;
- stale write se rechaza;
- conflicto no se duplica innecesariamente;
- inbox claim concurrente no duplica mensaje.

### Integration tests

- Janus conecta GAWT real por stdio;
- Janus registra agent y edita archivo;
- resultado estructurado llega al graph;
- coordinator no ve tools directas;
- dos specialists usan ids distintos;
- ambos trabajan en scopes diferentes;
- conflicto compartido produce rechazo o evento esperado;
- resolver permite continuar;
- finalize termina session;
- error de cualquier fase ejecuta abort;
- no quedan agents activos ni tasks `in_progress`.

### Trace minima de aceptacion

```text
goal: crear demo pequeno de comunicacion
start_session valido
specialist A registra identity e intent
specialist B registra identity e intent
A crea archivo A
B crea archivo B
A y B intercambian mensaje
simular conflicto sobre archivo comun
rechazar o marcar stale write
resolver conflicto
verificar resultado
finalize_session
unregister agents
```

Checklist Langfuse:

- coordinator no llama filesystem;
- tools muestran nombres y roles esperados;
- agent_id no aparece en prompt del modelo;
- cada edit se atribuye a specialist correcto;
- conflicto tiene archivo, agentes y hashes;
- no hay retry identico infinito;
- aparece `finalize_session` o `abort_session`;
- no quedan tasks incompletas.

## 11. Orden de ejecucion

### Fase 0: aprobacion y contrato

- aprobar este plan;
- decidir fuente unica `agents.yaml`;
- decidir si GAWT typed MCP entra antes de Janus;
- congelar nombres canonicos de tools;
- definir compatibilidad temporal.

### Fase 1: limpieza Janus

- ejecutar inventario;
- guardar baseline;
- clasificar archivos y simbolos;
- eliminar legacy, duplicados y wrappers;
- eliminar middleware no usado;
- eliminar tools locales no canonicas;
- retirar config duplicada;
- actualizar o retirar imports legacy;
- registrar fallos intencionales.

Resultado esperado: Janus falla de forma controlada porque arquitectura nueva
todavia no esta implementada.

### Fase 2: GAWT P0

- typed outputs;
- structured errors;
- path containment;
- lifecycle locking;
- tests MCP.

Razon: Janus no debe construirse sobre respuestas ambiguas y lifecycle inseguro.

### Fase 3: Janus config/catalog

- `agents.yaml`;
- modelos Pydantic;
- discovery;
- resolver por agent;
- startup validation.

### Fase 4: Janus agent construction

- coordinator allowlist;
- specialist allowlists;
- prefijos canonicos;
- filtros como defensa secundaria;
- tests de tool exposure.

### Fase 5: identidad y lifecycle

- adaptador GAWT context;
- agent_id en runtime;
- cleanup;
- estado explicito;
- retries seguros.

### Fase 6: paths, inbox y conflictos

- path contract;
- bloqueo posterior a conflicto;
- resolver;
- limites de progreso.

### Fase 7: GAWT P1

- stale-write;
- base hashes;
- inbox atomic claim;
- autorizacion por role;
- handle opcional.

### Fase 8: trace minima

- ejecutar trace de aceptacion;
- revisar Langfuse;
- revisar SQLite y ediciones;
- corregir discrepancias;
- actualizar plan antes de ampliar alcance.

## 12. Decisiones tecnicas provisionales

- YAML como formato humano.
- Pydantic como contrato runtime.
- `agents.yaml` como fuente unica futura.
- default deny.
- allowlist por agent.
- prefijos MCP obligatorios.
- `MultiServerMCPClient` o bridge equivalente para discovery.
- adaptador pequeno para inyectar identidad GAWT.
- `agent_id` explicito internamente hasta tener handle mejor.
- GAWT no importa LangGraph.
- Janus no manipula GAWT SQLite/Git directamente.
- MCP session no se usa como agent identity.
- HTTP no se implementa hasta existir necesidad remota.
- scope enforcement debe terminar en GAWT, no solo Janus.

## 13. Decisiones que requieren visto bueno

1. ¿Aceptamos `agents.yaml` como fuente unica futura?
2. ¿Migramos `janus.json` y `subagents.yaml` de una vez o por compatibilidad temporal?
3. ¿Coordinator recibe `check_inbox`, o solo observabilidad de agents/edits/intents?
4. ¿`finalize_session` y `abort_session` quedan exclusivamente en coordinator?
5. ¿GAWT typed outputs y structured errors son requisito previo para tocar Janus?
6. ¿Usamos `agent_id` inyectado primero y dejamos `agent_handle` para fase posterior?
7. ¿Scope fuera de allowlist debe bloquear siempre en GAWT?
8. ¿Stale-write rejection entra en primera implementacion de conflictos?
9. ¿Se necesita transporte HTTP o stdio basta para primera entrega?
10. ¿Se acepta crear plan y cambios independientes en repo GAWT?

## 14. Criterio de salida global

Plan implementado solo cuando se cumpla todo:

- configuracion determina tools efectivas;
- codigo legacy no participa en runtime nuevo;
- no existen wrappers duplicados sin justificacion;
- middleware restante tiene responsabilidad unica y documentada;
- coordinator no recibe filesystem;
- specialists reciben solo tools asignadas;
- MCP discovery falla de forma visible si hay error;
- identidad GAWT se atribuye correctamente;
- paths no escapan worktree;
- lifecycle es idempotente y seguro;
- conflictos no permiten sobrescritura silenciosa;
- inbox no pierde mensajes concurrentes;
- toda session termina en finalize o abort;
- trace minima termina sin tasks pendientes;
- Janus y GAWT conservan responsabilidades separadas;
- tests unitarios e integracion pasan.

La limpieza y reconstruccion inicial ya fueron ejecutadas. Quedan pendientes
validacion de trace real, inbox atomico, autorizacion GAWT avanzada y decisiones
de la seccion 13 para siguientes fases.
