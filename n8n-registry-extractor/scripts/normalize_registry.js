const fs = require("fs");
const path = require("path");

const INPUT_FILE = path.join(__dirname, "..", "n8n_registry.json");
const OUTPUT_FILE = path.join(__dirname, "..", "output", "n8n_registry_normalized.json");

function ensureOutputDir() {
  const outputDir = path.dirname(OUTPUT_FILE);
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }
}

function safeArray(value) {
  if (Array.isArray(value)) return value;
  if (value === undefined || value === null) return [];
  return [value];
}

function hasUsefulProperties(node) {
  return Array.isArray(node.properties) && node.properties.length > 0;
}

function isBadNode(node) {
  if (!node) return true;
  if (!node.node_type) return true;
  if (typeof node.node_type !== "string") return true;
  if (node.node_type.endsWith(".undefined")) return true;
  if (!node.display_name) return true;
  if (!node.name) return true;
  return false;
}

function normalizeVersion(version) {
  if (Array.isArray(version)) {
    return {
      versions: version,
      default_version: version[version.length - 1],
    };
  }

  if (version !== undefined && version !== null) {
    return {
      versions: [version],
      default_version: version,
    };
  }

  return {
    versions: [],
    default_version: null,
  };
}

function extractOptionsFromProperty(property) {
  if (!property || !Array.isArray(property.options)) return [];

  return property.options.map((option) => ({
    name: option.name || "",
    value: option.value,
    description: option.description || "",
    action: option.action || "",
  }));
}

function findProperty(properties, name) {
  return properties.find((property) => property.name === name);
}

function extractResources(properties) {
  const resourceProperty = findProperty(properties, "resource");
  return extractOptionsFromProperty(resourceProperty);
}

function extractOperations(properties) {
  const operationProperty = findProperty(properties, "operation");
  return extractOptionsFromProperty(operationProperty);
}

function extractRequiredFields(properties) {
  return properties
    .filter((property) => property.required === true)
    .map((property) => ({
      name: property.name,
      displayName: property.displayName || "",
      type: property.type || "",
      default: property.default,
      description: property.description || "",
      displayOptions: property.displayOptions || null,
    }));
}

function normalizeIO(value) {
  if (Array.isArray(value)) return value;

  if (typeof value === "string") {
    if (value.includes("={{")) {
      return {
        raw: value,
        normalized: ["main"],
        dynamic: true,
      };
    }

    return [value];
  }

  return [];
}

function buildSearchText(node, resources, operations) {
  return [
    node.display_name,
    node.name,
    node.description,
    node.node_type,
    resources.map((r) => `${r.name} ${r.value} ${r.description}`).join(" "),
    operations.map((o) => `${o.name} ${o.value} ${o.description} ${o.action}`).join(" "),
  ]
    .filter(Boolean)
    .join(" ")
    .replace(/\s+/g, " ")
    .trim();
}

function normalizeNode(node) {
  const properties = Array.isArray(node.properties) ? node.properties : [];
  const resources = extractResources(properties);
  const operations = extractOperations(properties);
  const versionInfo = normalizeVersion(node.version);

  const issues = [];

  if (!hasUsefulProperties(node)) {
    issues.push("Node has empty properties. It may be a wrapper or version loader.");
  }

  if (typeof node.inputs === "string" && node.inputs.includes("={{")) {
    issues.push("Node has dynamic inputs.");
  }

  if (typeof node.outputs === "string" && node.outputs.includes("={{")) {
    issues.push("Node has dynamic outputs.");
  }

  return {
    node_type: node.node_type,
    node_name: node.name,
    display_name: node.display_name,
    description: node.description || "",
    versions: versionInfo.versions,
    default_version: versionInfo.default_version,
    group: safeArray(node.group),
    inputs: normalizeIO(node.inputs),
    outputs: normalizeIO(node.outputs),
    credentials: safeArray(node.credentials),
    properties,
    resources,
    operations,
    required_fields: extractRequiredFields(properties),
    defaults: node.defaults || {},
    source_package: node.source_package || "",
    source_file: node.source_file || "",
    usable_as_tool: Boolean(node.usable_as_tool),
    search_text: buildSearchText(node, resources, operations),
    is_valid_for_generation: hasUsefulProperties(node),
    issues,
  };
}

function main() {
  ensureOutputDir();

  const raw = JSON.parse(fs.readFileSync(INPUT_FILE, "utf-8"));

  const normalizedNodes = [];
  const skippedNodes = [];

  for (const node of raw.nodes || []) {
    if (isBadNode(node)) {
      skippedNodes.push({
        node_type: node?.node_type || null,
        display_name: node?.display_name || null,
        reason: "Invalid node metadata or undefined node type",
      });
      continue;
    }

    const normalized = normalizeNode(node);

    if (!normalized.is_valid_for_generation) {
      skippedNodes.push({
        node_type: normalized.node_type,
        display_name: normalized.display_name,
        reason: "No useful properties",
      });
      continue;
    }

    normalizedNodes.push(normalized);
  }

  const output = {
    generated_at: new Date().toISOString(),
    source_generated_at: raw.generated_at,
    raw_node_count: raw.node_count,
    normalized_node_count: normalizedNodes.length,
    skipped_node_count: skippedNodes.length,
    credential_count: raw.credential_count || 0,
    nodes: normalizedNodes,
    credentials: raw.credentials || [],
    skipped_nodes: skippedNodes,
  };

  fs.writeFileSync(OUTPUT_FILE, JSON.stringify(output, null, 2));

  console.log(`Normalized nodes: ${normalizedNodes.length}`);
  console.log(`Skipped nodes: ${skippedNodes.length}`);
  console.log(`Output written to: ${OUTPUT_FILE}`);
}

main();