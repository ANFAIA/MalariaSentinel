---
name: memory-setup
description: Install, configure, and troubleshoot the MalariaSentinel knowledge graph memory module (Neo4j + Graphiti MCP). Covers Docker prerequisites, the install script, environment configuration, cold-start, health checks, and common failure modes. Use when setting up the memory module for the first time, diagnosing stack issues, or reconfiguring the knowledge graph.
---

# Memory Setup Skill

This skill covers the complete lifecycle of the MalariaSentinel knowledge graph memory module, from initial installation through troubleshooting and recovery.

## 1. Prerequisites

Before installing the memory module, ensure you have:

- **Docker Desktop** running (Neo4j + Graphiti MCP containers)
- **OpenAI API key** (for embeddings - `text-embedding-3-small`)
- **Neo4j password** (for database access)
- **Python 3.10+** with `uv` package manager

## 2. Installation

### Interactive Installation
```bash
bash agents/memory/install.sh
```
The installer will prompt for:
- Project name (default: `malariasentinel`)
- OpenAI API key
- Neo4j password
- Neo4j user (default: `neo4j`)
- Graphiti group ID (default: project name)
- Model name (default: `gpt-4o-mini`)
- Embedder model (default: `text-embedding-3-small`)

### Non-Interactive Installation
```bash
bash agents/memory/install.sh --project malariasentinel \
    --openai-key sk-... --neo4j-password ... --yes
```

### From Config File
```bash
bash agents/memory/install.sh --config /path/to/mem.env
```

Config file format (`mem.env`):
```
PROJECT=malariasentinel
OPENAI_API_KEY=sk-...
NEO4J_PASSWORD=...
NEO4J_USER=neo4j
GRAPHITI_GROUP_ID=malariasentinel
MODEL_NAME=gpt-4o-mini
EMBEDDER_MODEL=text-embedding-3-small
```

## 3. What install.sh Does

The installer performs these steps:

1. **Writes `.project`** - Sets the Neo4j `group_id` for project isolation
2. **Generates `.env`** - Creates `agents/memory/runtime/.env` with credentials
3. **Copies opencode-stubs** - Installs custom tools to `.opencode/tools/`
4. **Patches `opencode.json`** - Adds memory tool permissions and configuration
5. **Patches `.gitignore`** - Excludes sensitive files from version control

## 4. Cold-Start

After installation, run the bootstrap to initialize the knowledge graph:

```bash
make -f agents/memory/scripts/Makefile bootstrap
```

This will:
- Start Neo4j and Graphiti MCP containers
- Create the schema (8 labels)
- Apply seed data from `agents/memory/seed/<project>.yaml`
- Load bootstrap entries from `agents/memory/bootstrap/`

## 5. Health Checks

### Status Check
```bash
make -f agents/memory/scripts/Makefile status
```
Returns:
- Docker container status (Neo4j + Graphiti MCP)
- Neo4j connection test
- Graphiti MCP health probe
- File system state

### Schema Audit
```bash
make -f agents/memory/scripts/Makefile audit
```
Validates 3 invariants:
1. No `Entity`-only nodes (every node has at least one schema label)
2. No orphan relations (every rel endpoint exists)
3. No out-of-schema labels (all labels are in `config.yaml`)

## 6. The 8 Schema Labels

The knowledge graph uses these typed labels:

| Label | Purpose |
|---|---|
| `Component` | System components, modules, services |
| `Investigation` | Research questions, bugs, explorations |
| `Architecture` | Design decisions, ADRs, patterns |
| `Pattern` | Recurring solutions, conventions |
| `Pitfall` | Known issues, gotchas, anti-patterns |
| `Tool` | External tools, libraries, dependencies |
| `Operational` | Milestones, processes, workflows |
| `Preference` | User/team preferences, conventions |

Schema definition: `agents/memory/runtime/config/config.yaml`

## 7. The 6 Trees

The knowledge graph organizes nodes into a hierarchical tree structure:

1. **Centinela** (`obj-centinela-sdss`) - Top-level project object
2. **Pipeline** (`comp-centinela`) - Core system components
3. **Research** (`research-knowledge-base`) - Research findings and investigations
4. **Agents & Memory** (`agents-module`) - Agent infrastructure and memory system
5. **Wisdom** (`project-wisdom`) - Patterns, pitfalls, and conventions
6. **Architecture** (`architecture-decisions`) - Design decisions and ADRs

## 8. Common Failures and Fixes

### Docker Not Running
**Symptom**: `Cannot connect to Docker daemon`
**Fix**: Start Docker Desktop, wait for it to be fully running

### Neo4j Connection Refused
**Symptom**: `Unable to connect to bolt://localhost:7687`
**Fix**: 
1. Check Docker containers: `docker ps | grep neo4j`
2. Restart containers: `docker compose -f agents/memory/runtime/docker-compose.yml restart`
3. Check port conflicts: `lsof -i :7687`

### OpenAI Key Invalid
**Symptom**: `AuthenticationError` or `Invalid API key`
**Fix**:
1. Verify key in `agents/memory/runtime/.env`
2. Test key: `curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"`
3. Regenerate key if needed

### Embedding Failures
**Symptom**: `Embedding model not found` or dimension mismatch
**Fix**:
1. Check `EMBEDDER_MODEL` in `.env` (should be `text-embedding-3-small`)
2. Run re-embed: `bash agents/memory/scripts/reembed.sh`

### Schema Violations
**Symptom**: `audit` returns non-zero counts
**Fix**:
1. Check for unlabeled nodes: `memory_query "MATCH (n) WHERE NOT EXISTS(n.label) RETURN n"`
2. Check for orphan rels: `memory_query "MATCH (a)-[r]->(b) WHERE NOT EXISTS(a.uuid) OR NOT EXISTS(b.uuid) RETURN r"`
3. Check labels: `agents/memory/runtime/config/config.yaml`

## 9. Recovery

### Re-embed All Nodes
```bash
bash agents/memory/scripts/reembed.sh
```
Regenerates embeddings for all nodes (useful after model changes).

### Seed Reset
```bash
make -f agents/memory/scripts/Makefile seed
```
Re-applies seed data from `agents/memory/seed/<project>.yaml`.

### Full Wipe (Requires Approval)
```bash
make -f agents/memory/scripts/Makefile wipe
```
⚠️ **Destructive**: Deletes all data and resets to clean state. Requires explicit user approval.

## 10. Related Skills

- **project-memory**: How to use the knowledge graph (read/write nodes, relations, episodes)
- **agent-ops**: Session lifecycle management (start, end, audit)
- **memory-setup**: This skill (installation and troubleshooting)

## Quick Reference

```bash
# Install
bash agents/memory/install.sh --project malariasentinel --openai-key sk-... --neo4j-password ... --yes

# Cold-start
make -f agents/memory/scripts/Makefile bootstrap

# Health check
make -f agents/memory/scripts/Makefile status

# Audit
make -f agents/memory/scripts/Makefile audit

# Seed
make -f agents/memory/scripts/Makefile seed

# Re-embed
bash agents/memory/scripts/reembed.sh

# Wipe (careful!)
make -f agents/memory/scripts/Makefile wipe
```