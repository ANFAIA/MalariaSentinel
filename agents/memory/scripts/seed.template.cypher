// Module: agents/memory — see AGENTS.md (Protected files) and opencode.json permission.edit.

// agents/memory/scripts/seed.template.cypher
// Reference template for what a seed Cypher looks like once seed.sh has
// compiled the project yaml. NOT executed directly. The actual generated
// cypher is what seed.sh pipes into `neo4j-cli query --atomic --rw`.
//
// Read this file to understand the shape of a valid seed. Do not edit it
// to "tweak the seed" — edit seed/<project>.yaml and re-run seed.sh.

// ============================================================
// NODES (one MERGE per node, idempotent by uuid + group_id)
// ============================================================

// Components
MERGE (n:Entity:Component {uuid: 'pkg-mal-core', group_id: 'malariasentinel'})
  ON CREATE SET n.name = 'mal-core',
                n.summary = 'Stable pipeline logic. Empty; ready for promotion.',
                n.path = 'mal-core/',
                n.created_at = datetime()
  ON MATCH  SET n.name = 'mal-core',
                n.summary = 'Stable pipeline logic. Empty; ready for promotion.',
                n.path = 'mal-core/';

// Investigations
MERGE (n:Entity:Investigation {uuid: 'inv-malariasentinel', group_id: 'malariasentinel'})
  ON CREATE SET n.name = 'MalariaSentinel',
                n.summary = 'Build a malaria Sentinel / SDSS...',
                n.status = 'open',
                n.created_at = datetime()
  ON MATCH  SET n.name = 'MalariaSentinel',
                n.summary = 'Build a malaria Sentinel / SDSS...',
                n.status = 'open';

// Pitfalls
MERGE (n:Entity:Pitfall {uuid: 'pitfall-supermemory-deprecated', group_id: 'malariasentinel'})
  ON CREATE SET n.name = 'PITFALL-supermemory-deprecated',
                n.summary = 'The supermemory tool is a generic system template...',
                n.created_at = datetime()
  ON MATCH  SET n.name = 'PITFALL-supermemory-deprecated',
                n.summary = 'The supermemory tool is a generic system template...';

// Preferences
MERGE (n:Entity:Preference {uuid: 'pref-supermemory-globally-deprecated', group_id: 'malariasentinel'})
  ON CREATE SET n.name = 'PREF-supermemory-globally-deprecated',
                n.summary = 'User preference: supermemory is descatalogated...',
                n.created_at = datetime()
  ON MATCH  SET n.name = 'PREF-supermemory-globally-deprecated',
                n.summary = 'User preference: supermemory is descatalogated...';

// Architecture
MERGE (n:Entity:Architecture {uuid: 'arch-forbidden-tools', group_id: 'malariasentinel'})
  ON CREATE SET n.name = 'FORBIDDEN TOOLS section',
                n.summary = 'The top section of AGENTS.md that declares tools the agent must not invoke...',
                n.created_at = datetime()
  ON MATCH  SET n.name = 'FORBIDDEN TOOLS section',
                n.summary = 'The top section of AGENTS.md that declares tools the agent must not invoke...';

// Tools
MERGE (n:Entity:Tool {uuid: 'tool-neo4j-cli', group_id: 'malariasentinel'})
  ON CREATE SET n.name = 'neo4j-cli',
                n.summary = 'CLI for direct Cypher against the project Neo4j...',
                n.created_at = datetime()
  ON MATCH  SET n.name = 'neo4j-cli',
                n.summary = 'CLI for direct Cypher against the project Neo4j...';

// Patterns
MERGE (n:Entity:Pattern {uuid: 'pattern-sdss-framework', group_id: 'malariasentinel'})
  ON CREATE SET n.name = 'SDSS framework',
                n.summary = 'Kelly 2012. SDSS = inputs (data + expert)...',
                n.created_at = datetime()
  ON MATCH  SET n.name = 'SDSS framework',
                n.summary = 'Kelly 2012. SDSS = inputs (data + expert)...';

// Operational
MERGE (n:Entity:Operational {uuid: 'op-bring-up-memory', group_id: 'malariasentinel'})
  ON CREATE SET n.name = 'bring-up-memory',
                n.summary = 'cd memory && docker compose up -d',
                n.created_at = datetime()
  ON MATCH  SET n.name = 'bring-up-memory',
                n.summary = 'cd memory && docker compose up -d';

// ============================================================
// RELATIONS (one MATCH + MERGE per edge, validated by the add-rel.sh guard)
// ============================================================

MATCH (a:Entity {uuid: 'inv-malariasentinel', group_id: 'malariasentinel'})
MATCH (b:Entity {uuid: 'inv-h1-simulation-unet', group_id: 'malariasentinel'})
MERGE (a)-[r:TESTS {group_id: 'malariasentinel'}]->(b)
  ON CREATE SET r.created_at = datetime()
  ON MATCH  SET r.created_at = datetime();

MATCH (a:Entity {uuid: 'inv-h1-simulation-unet', group_id: 'malariasentinel'})
MATCH (b:Entity {uuid: 'tool-unet-surrogate', group_id: 'malariasentinel'})
MERGE (a)-[r:USES {group_id: 'malariasentinel'}]->(b)
  ON CREATE SET r.created_at = datetime()
  ON MATCH  SET r.created_at = datetime();
