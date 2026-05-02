/**
 * build_operation_index.js (FIXED)
 * ---------------------------------
 * Reads n8n_registry_normalized.json and builds a flat operation index
 * where each record = one actionable thing the agent can do.
 *
 * Properly handles:
 *   - Nodes with resource + operation (e.g. Slack: message → post)
 *   - Nodes with operation only (no resource grouping)
 *   - Trigger nodes and simple nodes (single entry, no resource/operation)
 *   - displayOptions-aware required field resolution
 *
 * Output: output/n8n_operation_index.json
 *
 * Usage:
 *   node scripts/build_operation_index.js
 */

const fs = require("fs");
const path = require("path");

// ─── Paths ───────────────────────────────────────────────────────────────────

const NORMALIZED_PATH = path.join(
  __dirname,
  "../output/n8n_registry_normalized.json"
);
const OUTPUT_PATH = path.join(
  __dirname,
  "../output/n8n_operation_index.json"
);

// ─── Load normalized registry ────────────────────────────────────────────────

if (!fs.existsSync(NORMALIZED_PATH)) {
  console.error("ERROR: n8n_registry_normalized.json not found.");
  console.error("Run normalize_registry.js first.");
  process.exit(1);
}

const registry = JSON.parse(fs.readFileSync(NORMALIZED_PATH, "utf-8"));
const nodes = registry.nodes || [];
console.log(`Loaded ${nodes.length} normalized nodes`);

// ─── Helpers ─────────────────────────────────────────────────────────────────

/**
 * Extract resource options from a node's properties array.
 * Looks for a property named "resource" with type "options".
 */
function extractResources(properties) {
  if (!Array.isArray(properties)) return [];
  const resourceProp = properties.find(
    (p) => p.name === "resource" && p.type === "options"
  );
  if (!resourceProp || !Array.isArray(resourceProp.options)) return [];
  return resourceProp.options.map((opt) => ({
    value: opt.value,
    name: opt.name || opt.value,
  }));
}

/**
 * Extract operation options from a node's properties array,
 * optionally filtered by a specific resource value.
 */
function extractOperations(properties, resourceValue) {
  if (!Array.isArray(properties)) return [];

  const operationProps = properties.filter(
    (p) => p.name === "operation" && p.type === "options"
  );

  if (operationProps.length === 0) return [];

  // Find the operation property that matches this resource
  let matchedProp = null;

  if (resourceValue) {
    // Find operation prop whose displayOptions.show.resource includes this resource
    matchedProp = operationProps.find((p) => {
      const show = p.displayOptions?.show;
      if (!show) return false;
      const resourceFilter = show.resource || show.Resource;
      if (!resourceFilter) return false;
      return Array.isArray(resourceFilter)
        ? resourceFilter.includes(resourceValue)
        : resourceFilter === resourceValue;
    });

    // If no resource-specific one found, fall back to any operation without displayOptions
    if (!matchedProp) {
      matchedProp = operationProps.find((p) => !p.displayOptions);
    }
  } else {
    // No resource — just take the first operation property
    matchedProp = operationProps[0];
  }

  if (!matchedProp || !Array.isArray(matchedProp.options)) return [];

  return matchedProp.options.map((opt) => ({
    value: opt.value,
    name: opt.name || opt.value,
    description: opt.description || opt.action || "",
  }));
}

/**
 * Resolve required fields for a specific resource+operation combination.
 * A field is required for this combo if:
 *   1. It has required: true
 *   2. Its displayOptions.show matches the given resource and operation
 *      (or it has no displayOptions, meaning it's always visible)
 */
function resolveRequiredFields(properties, resourceValue, operationValue) {
  if (!Array.isArray(properties)) return [];

  const required = [];

  for (const prop of properties) {
    // Skip resource and operation fields themselves
    if (prop.name === "resource" || prop.name === "operation") continue;
    // Skip non-required fields
    if (!prop.required) continue;

    const show = prop.displayOptions?.show;

    if (!show) {
      // No displayOptions — always visible and required
      required.push(buildFieldRecord(prop));
      continue;
    }

    const resourceFilter = show.resource || show.Resource;
    const operationFilter = show.operation || show.Operation;

    // Check resource match
    if (resourceFilter && resourceValue) {
      const resourceMatches = Array.isArray(resourceFilter)
        ? resourceFilter.includes(resourceValue)
        : resourceFilter === resourceValue;
      if (!resourceMatches) continue;
    }

    // Check operation match
    if (operationFilter && operationValue) {
      const operationMatches = Array.isArray(operationFilter)
        ? operationFilter.includes(operationValue)
        : operationFilter === operationValue;
      if (!operationMatches) continue;
    }

    required.push(buildFieldRecord(prop));
  }

  return required;
}

function buildFieldRecord(prop) {
  return {
    name: prop.name,
    displayName: prop.displayName || prop.name,
    type: prop.type || "string",
    default: prop.default !== undefined ? prop.default : null,
    description: (prop.description || "").substring(0, 200),
  };
}

/**
 * Extract credentials from a node.
 */
function extractCredentials(node) {
  const creds = node.credentials || [];
  if (!Array.isArray(creds)) return [];
  return creds.map((c) => (typeof c === "string" ? c : c.name || c));
}

/**
 * Build search text for an operation record.
 */
function buildSearchText(node, resource, resourceName, operation, operationName, action) {
  const parts = [
    node.display_name || "",
    node.node_name || "",
    resourceName || resource || "",
    operationName || operation || "",
    action || "",
    node.description || "",
    node.node_type || "",
  ];
  return parts
    .filter(Boolean)
    .join(" ")
    .replace(/\s+/g, " ")
    .trim()
    .substring(0, 500);
}

// ─── Main indexer ─────────────────────────────────────────────────────────────

const operations = [];
let processedNodes = 0;
let skippedNodes = 0;
let simpleNodes = 0;
let resourceOperationNodes = 0;

for (const node of nodes) {
  if (!node.is_valid_for_generation) {
    skippedNodes++;
    continue;
  }

  const properties = Array.isArray(node.properties) ? node.properties : [];
  const credentials = extractCredentials(node);
  const resources = extractResources(properties);
  const defaultVersion = node.default_version || 1;

  if (resources.length > 0) {
    // ── Node has resources (e.g. Slack: message, channel, file) ──
    resourceOperationNodes++;

    for (const resource of resources) {
      const ops = extractOperations(properties, resource.value);

      if (ops.length > 0) {
        // Node has resource + operations
        for (const op of ops) {
          const requiredFields = resolveRequiredFields(
            properties,
            resource.value,
            op.value
          );

          operations.push({
            node_type: node.node_type,
            node_name: node.node_name,
            display_name: node.display_name,
            default_version: defaultVersion,
            resource: resource.value,
            resource_name: resource.name,
            operation: op.value,
            operation_name: op.name,
            action: op.description || `${op.name} ${resource.name}`,
            description: node.description || "",
            credentials,
            required_fields: requiredFields,
            search_text: buildSearchText(
              node,
              resource.value,
              resource.name,
              op.value,
              op.name,
              op.description
            ),
          });
        }
      } else {
        // Resource exists but no operations — create resource-level entry
        const requiredFields = resolveRequiredFields(
          properties,
          resource.value,
          null
        );

        operations.push({
          node_type: node.node_type,
          node_name: node.node_name,
          display_name: node.display_name,
          default_version: defaultVersion,
          resource: resource.value,
          resource_name: resource.name,
          operation: null,
          operation_name: null,
          action: resource.name,
          description: node.description || "",
          credentials,
          required_fields: requiredFields,
          search_text: buildSearchText(
            node,
            resource.value,
            resource.name,
            null,
            null,
            null
          ),
        });
      }
    }
  } else {
    // ── Node has no resources — check for operations only ──
    const ops = extractOperations(properties, null);

    if (ops.length > 0) {
      // Node has operations but no resources (e.g. some simple nodes)
      for (const op of ops) {
        const requiredFields = resolveRequiredFields(
          properties,
          null,
          op.value
        );

        operations.push({
          node_type: node.node_type,
          node_name: node.node_name,
          display_name: node.display_name,
          default_version: defaultVersion,
          resource: null,
          resource_name: null,
          operation: op.value,
          operation_name: op.name,
          action: op.description || op.name,
          description: node.description || "",
          credentials,
          required_fields: requiredFields,
          search_text: buildSearchText(
            node,
            null,
            null,
            op.value,
            op.name,
            op.description
          ),
        });
      }
    } else {
      // ── Simple/trigger node — create single entry ──
      simpleNodes++;
      const requiredFields = resolveRequiredFields(properties, null, null);

      operations.push({
        node_type: node.node_type,
        node_name: node.node_name,
        display_name: node.display_name,
        default_version: defaultVersion,
        resource: null,
        resource_name: null,
        operation: null,
        operation_name: null,
        action: node.description || node.display_name || "",
        description: node.description || "",
        credentials,
        required_fields: requiredFields,
        search_text: buildSearchText(node, null, null, null, null, null),
      });
    }
  }

  processedNodes++;
}

// ─── Write output ─────────────────────────────────────────────────────────────

const output = {
  generated_at: new Date().toISOString(),
  operation_count: operations.length,
  processed_nodes: processedNodes,
  skipped_nodes: skippedNodes,
  simple_nodes: simpleNodes,
  resource_operation_nodes: resourceOperationNodes,
  operations,
};

fs.mkdirSync(path.dirname(OUTPUT_PATH), { recursive: true });
fs.writeFileSync(OUTPUT_PATH, JSON.stringify(output, null, 2));

// ─── Summary ──────────────────────────────────────────────────────────────────

console.log("\n" + "=".repeat(55));
console.log("  Operation Index Built Successfully");
console.log("=".repeat(55));
console.log(`  Processed nodes:          ${processedNodes}`);
console.log(`  Skipped (invalid) nodes:  ${skippedNodes}`);
console.log(`  Resource+operation nodes: ${resourceOperationNodes}`);
console.log(`  Simple/trigger nodes:     ${simpleNodes}`);
console.log(`  Total operation records:  ${operations.length}`);
console.log(`  Output: ${OUTPUT_PATH}`);
console.log("=".repeat(55));

// ─── Quick spot check ─────────────────────────────────────────────────────────

const keyword = process.argv[2] || "slack";
const sample = operations.filter(
  (o) =>
    (o.display_name || "").toLowerCase().includes(keyword) ||
    (o.node_type || "").toLowerCase().includes(keyword)
);

console.log(`\n  Spot check — "${keyword}" (${sample.length} records):`);
sample.slice(0, 8).forEach((o) => {
  const res = o.resource_name || "(no resource)";
  const op = o.operation_name || "(no operation)";
  const req = (o.required_fields || []).map((f) => f.name || f).join(", ") || "none";
  console.log(`    ${o.display_name} | ${res} → ${op} | req: ${req}`);
});