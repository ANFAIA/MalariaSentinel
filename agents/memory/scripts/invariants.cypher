// Module: agents/memory — see AGENTS.md (Protected files) and opencode.json permission.edit.

// agents/memory/scripts/invariants.cypher
// The three schema invariants. Each statement is a single count/dump query
// that audit.sh runs in its own transaction. A non-zero result on any of
// them is a schema violation that the seed pipeline must not produce.
//
// Two placeholders are substituted at runtime by audit.sh:
//   __GROUP_ID__        — the project's group_id (from agents/memory/.project)
//   __SCHEMA_LABELS__   — the schema's label list (from runs/schema.cache)

// Invariant 1: no Entity node without a secondary label.
// A :Entity-only node means the LLM extractor absorbed a value that did not
// match any schema label, OR a write bypassed agents/memory/scripts/. Either way,
// the node is ungoverned.
MATCH (n:Entity) WHERE n.group_id = '__GROUP_ID__' AND size(labels(n)) = 1 RETURN count(n) AS unlabeled;

// Invariant 2: no relation with a missing endpoint.
// Either src or dst was deleted but the rel survived, or it was created
// against a typo. Either way it is corrupt and will break traversal.
MATCH (a)-[r]->(b) WHERE r.group_id = '__GROUP_ID__' AND (a IS NULL OR b IS NULL) RETURN count(r) AS orphans;

// Invariant 3: no label outside the schema.
// The schema is fixed at memory/config/config.yaml (lines 81-99). Any new
// label is a bug — either an extractor hallucination or a forgotten config
// update. Label list is substituted in by audit.sh from runs/schema.cache
// so adding a label to the config auto-flows here.
MATCH (n) WHERE n.group_id = '__GROUP_ID__' UNWIND labels(n) AS lbl WITH lbl WHERE lbl <> 'Entity' AND NOT lbl IN [__SCHEMA_LABELS__] RETURN DISTINCT lbl AS out_of_schema;

// Bonus dump: distribution by label. Not an invariant (zero is allowed for
// some labels), but useful for sanity-checking that the seed has the shape
// you expect. Comment out if you want strict mode.
MATCH (n) WHERE n.group_id = '__GROUP_ID__' UNWIND labels(n) AS lbl WITH lbl WHERE lbl <> 'Entity' RETURN lbl, count(*) AS n ORDER BY n DESC;
