# Actualización diaria de la base de conocimiento

## Objetivo

Revisar los commits recientes y producir un plan estructurado de actualización de la base de conocimiento. **Modo plan: no ejecutar escrituras.** El output es un plan que el memory-curator ejecutará después.

## Protocolo

### Paso 1 — Ver commits recientes
```bash
git log --oneline -20
```

### Paso 2 — Entender cada commit
Para cada commit relevante:
```bash
git show --stat <sha>
git log -1 --format="%H %s" <sha>
```

### Paso 3 — Recall: ¿qué ya existe en el KG?
Ejecutar en paralelo:
- `memory_recall({ query: "M<n> <milestone name>", k: 5 })` para cada milestone relevante
- `memory_recall({ query: "<component or feature name>", k: 5 })` para componentes nuevos
- `memory_query({ cypher: "MATCH (n:Operational) WHERE n.name =~ 'M.*' RETURN n.uuid, n.name ORDER BY n.name" })` para ver milestones

### Paso 4 — Identificar gaps
Para cada commit, determinar:
- ¿El cambio ya está registrado en el KG? (comparar UUIDs y fechas)
- ¿Es un cambio significativo para el KG? (un fix de typo de 1 línea no califica)
- ¿Qué tipo de nodo corresponde? (Component, Operational, Pitfall, Pattern, Tool, Architecture, Investigation)

### Paso 5 — Clasificar cada gap

| Tipo de cambio | Label | Árbol | Parent típico |
|---|---|---|---|
| Milestone nuevo o actualizado | Operational | Centinela | obj-centinela-sdss |
| Componente nuevo (package, servicio, archivo significativo) | Component | Pipeline | comp-centinela |
| Bug encontrado y mitigado | Pitfall | Wisdom | project-wisdom |
| Solución reutilizable descubierta | Pattern | Wisdom | project-wisdom |
| Herramienta nueva adoptada | Tool | Wisdom | project-wisdom |
| Decisión arquitectónica | Architecture | Architecture | architecture-decisions |
| Hilo de investigación | Investigation | Research | el milestone más relevante |

### Paso 6 — Producir el plan estructurado

## Formato de output

El agente DEBE producir un plan en este formato exacto:

```markdown
## KB Update Plan — YYYY-MM-DD

### Commits revisados
- <sha> <subject> — <cambios relevantes>
- <sha> <subject> — <cambios relevantes>
...

### Updates (nodos existentes a modificar)
| UUID | Tipo | Campos a actualizar |
|------|------|---------------------|
| op-m3-m4-unet | Operational | summary: "DONE 2026-07-19 via commit e366b38..." |

### Creates (nodos nuevos)
| UUID | Tipo | Parent | Nombre | Summary (breve) |
|------|------|--------|--------|-----------------|
| comp-m5-sdss-shell | Component | comp-centinela | M5 SDSS shell | FastAPI + Typer SDSS shell... |

### Connections (aristas laterales)
| Tipo | UUID origen | UUID destino |
|------|-------------|--------------|
| IMPLEMENTS | op-m5-sdss-shell-scaffold | comp-m5-sdss-shell |

### Episode
Nombre: session-YYYY-MM-DD: <resumen de una línea>
Cuerpo: <resumen de 10-20 líneas de todos los cambios>

### Audit
Ejecutar `memory_audit` después de la ejecución → esperar 0/0/0
```

## Reglas

1. **Modo plan**: NO ejecutar writes. Solo producir el plan.
2. **Recall antes del plan**: siempre verificar qué existe antes de proponer nodos nuevos.
3. **Schema estricto**: 8 labels solamente (Component, Investigation, Architecture, Pattern, Pitfall, Tool, Operational, Preference).
4. **UUIDs en kebab-case**: `comp-m5-sdss-shell`, `op-m3-m4-unet`.
5. **Todo nodo nuevo excepto roots necesita parent UUID**.
6. **8 verbos laterales**: USES, IMPLEMENTS, VALIDATES, REFERENCES, RELEVANT_TO, SUPERSEDES, BLOCKS, MITIGATED_BY.
7. **Si un commit es demasiado menor** (fix de typo de 1 línea), saltarlo y anotar por qué.

## Ejemplo de output

```markdown
## KB Update Plan — 2026-07-20

### Commits revisados
- e366b38 feat(M3-M4): U-Net surrogate training pipeline — 4 modules promoted to mal-core/
- a6cd0f7 feat(M5): SDSS shell with FastAPI + Typer — 6 modules in mal-core/
- 63a63b3 feat(M6): end-to-end SDSS run — env stack + ABM state loader + predict pipeline

### Updates
| UUID | Tipo | Campos |
|------|------|---------|
| op-m3-m4-unet | Operational | summary: "DONE 2026-07-19 via e366b38..." |
| op-m5-sdss-shell-scaffold | Operational | summary: "DONE 2026-07-19 via a6cd0f7..." |

### Creates
| UUID | Tipo | Parent | Nombre | Summary |
|------|------|--------|--------|---------|
| comp-m3-m4-unet-pipeline | Component | comp-centinela | M3-M4 U-Net pipeline | unet.py, dataset.py, train.py, unet_wrapper.py |
| comp-m5-sdss-shell | Component | comp-centinela | M5 SDSS shell | server.py, cli.py, aoi.py, scenario.py, registry.py, predict.py |

### Connections
| Tipo | Origen | Destino |
|------|--------|---------|
| IMPLEMENTS | op-m3-m4-unet | comp-m3-m4-unet-pipeline |
| IMPLEMENTS | op-m5-sdss-shell-scaffold | comp-m5-sdss-shell |
| USES | comp-m5-sdss-shell | tool-typer |
```
