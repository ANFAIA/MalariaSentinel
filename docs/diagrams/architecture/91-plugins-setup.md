---
title: Plugins setup · Breadcrumbs + Dataview
tags: [abm, meta, plugins]
tier: meta
---
up:: [[00-INDEX]]

# 91 · Setup de plugins — edges etiquetadas junto a la nota

Qué te da cada pieza y qué queda configurado.

## Instalado (ya en el vault)

| Plugin | Versión | Rol |
|---|---|---|
| **Breadcrumbs** | 4.22.1 | Typed edges: Matrix View / Tree / trail / codeblocks mermaid con label de edge / Export to Canvas |
| **Dataview** | 0.5.68 | Tablas de conexión generadas desde frontmatter |

Archivos: `docs/.obsidian/plugins/{breadcrumbs,dataview}/` + `community-plugins.json` ya los habilita. *Si tu Obsidian es < 1.14, Breadcrumbs 4.22.1 no carga — instala la versión compatible desde la comunidad (Settings → Community plugins → Browse → "Breadcrumbs").*

## Config Edge Fields ya escrita (`plugins/breadcrumbs/data.json`)

Fields registrados: `up`, `down`, `related`, `calls`, `called_by`, `owns`, `reads`, `writes`. Si Obsidian no los pilla al abrir (fue escrito a mano, formato interno puede migrar en futuras versiones), re-crea a mano en 2 min: *Settings → Breadcrumbs → Edge Fields → añadir los 8 de arriba*.

## Flujo de trabajo diario

1. Abre cualquier nota de módulo (p.ej. [[23-mosquito-submodel]]).
2. Arriba de la nota verás el **codeblock embeddings**:
   - bloque `breadcrumbs` mermaid → grafo local con flechas etiquetadas (`-- calls -->`, `-- owns -->`).
   - callout **Conexiones exactas del grafo** → para cada edge: método llamador, destino, archivo y firma.
3. `Cmd+P` → **Breadcrumbs: Open Matrix View** → panel lateral agrupando entrante/saliente por tipo de edge.
4. `Cmd+P` → **Breadcrumbs: Rebuild Graph** después de editar frontmatter (o edits al vuelo en `up::`).
5. `Breadcrumbs: Export to Canvas` sobre una nota → canvas nativo con edges etiquetadas, editable y exportable a imagen.

## Regeneración de bloques

Los bloques auto-generados viven entre marcadores `<!-- bc:auto:start -->` … `<!-- bc:auto:end -->`. Para regenerar tras editar una tabla Conexiones o el frontmatter:

```sh
uv run python docs/diagrams/architecture/scripts/inject_breadcrumbs.py
```

Idempotente: reemplaza el bloque existente, no duplica.

## ¿Y los tooltips de edge con la firma completa?

El comentario exacto (función/clase que une dos notas) vive en la **tabla Conexiones** auto-reflejada en el callout de cada nota + en el **Matrix View**; los edges del frontmatter (`calls` etc.) son los que Breadcrumbs dibuja. Juggl daría tooltip on-hover sobre la arista en un grafo interactivo, pero el plugin lleva años sin mantenimiento (v1.0.1, 2021) — riesgo de crash en Obsidian moderno. Si algún día lo quieres probar: community plugin *"Juggl"*, activa *Hover on Edges*; las aristas se etiquetan desde inline fields (`campo:: [[]]`), que el script podría generar. No lo activamos por defecto.

up:: [[00-INDEX]] · related:: [[90-convenciones]]