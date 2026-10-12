---
title: Convenciones del vault
tags: [abm, meta]
tier: meta
---
up:: [[00-INDEX]]

# 90 · Convenciones — taxonomía de edges y cómo extender

## Tipos de relación (tabla de edges)

| Edge YAML | Significado | Ejemplo |
|---|---|---|
| `calls:` | A invoca a B (método o API) | Engine → CoordinatorModel |
| `called_by:` | inverso de calls (ya listado para Graph View) | Coordinator ← Engine |
| `owns:` | A es dueño (unique_ptr / campo directo) | Engine owns MosquitoSubmodel |
| `reads:` | A lee datos de B sin llamada fuerte (const view / puntero) | Transmission lee BiteLedger |
| `writes:` | A escribe estado en B | Submodel escribe cohortes (add_eggs) |
| `up::` | jerarquía Breadcrumbs | cada nota sube a su padre |
| `related::` | puntual, sin jerarquía | dispersal ↔ wind_field |

## Notas por tier

| tier | Significado | Carpeta |
|---|---|---|
| index | hub raíz | raíz (00-INDEX) |
| overview | visión de capas | raíz (10-sistema) |
| core-flow | flujo temporal crítico | raíz (15-bucle-diario) |
| module | una clase/cpp | 20-modulos/ · 40-python/ |
| contract | tipos + constantes cross-módulo | raíz (30/31) |
| meta | convenciones | raíz (90) |

## Fuentes de verdad

- **Grafo CALLS/IMPORTS**: índice `codebase-memory` del repo (130 aristas CALLS del módulo abm, 199 aristas IMPORTS). Los edges de las notas se extrajeron de ahí y se verificaron leyendo `engine.cpp` (step: 537-597) y `mosquito_submodel.cpp` (advance_day: 466-1120).
- Antes de añadir una edge nueva a una nota: verifica en el `.cpp` — esta tabla es contrato, no suposición.

## Cómo añadir una nota nueva

1. Copia el patrón de cualquier nota de `20-modulos/` (frontmatter completo, tabla Conexiones, mermaid, `up::`).
2. Añade el wikilink en [[00-INDEX]] (sección navegación + orden de lectura).
3. Si el nodo entra en el canvas, añade nodo+edges en `abm-architecture.canvas` (formato JSON nativo Obsidian).
4. No edites el YAML a mano a ciegas — el frontmatter es el grafo; un typo rompe el Graph View.

## Convención de nombres

- Notas de módulo: `NN-nombre.md` (NN = orden de lectura).
- Nodo canvas: `id` = nombre corto del componente.
- Edge label = la llamada exacta con firma (`sub_->advance_day(patch_states)`) — en canvas: cadena corta.

up:: [[00-INDEX]]