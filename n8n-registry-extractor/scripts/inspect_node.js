#!/usr/bin/env node

/**
 * inspect_node.js
 * ---------------
 * CLI tool to verify registry quality for a specific node keyword.
 * Searches both n8n_registry_normalized.json and n8n_operation_index.json.
 *
 * Usage:
 *   node scripts/inspect_node.js slack
 *   node scripts/inspect_node.js gmail
 *   node scripts/inspect_node.js google
 *   node scripts/inspect_node.js http
 *   node scripts/inspect_node.js merge
 *   node scripts/inspect_node.js apify
 *   node scripts/inspect_node.js openai
 *   node scripts/inspect_node.js webhook
 *
 * Optional flags:
 *   --full       Show full properties array for matched nodes
 *   --ops-only   Show only operation index results
 *   --nodes-only Show only normalized registry results
 *   --json       Output raw JSON (no pretty print formatting)
 */

const fs = require("fs");
const path = require("path");

// ─── Config ────────────────────────────────────────────────────────────────

const NORMALIZED_PATH = path.join(
  __dirname,
  "../output/n8n_registry_normalized.json"
);
const OPERATION_INDEX_PATH = path.join(
  __dirname,
  "../output/n8n_operation_index.json"
);

// ─── ANSI Colors ────────────────────────────────────────────────────────────

const C = {
  reset: "\x1b[0m",
  bold: "\x1b[1m",
  dim: "\x1b[2m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  cyan: "\x1b[36m",
  red: "\x1b[31m",
  magenta: "\x1b[35m",
  blue: "\x1b[34m",
  white: "\x1b[37m",
  bgBlue: "\x1b[44m",
  bgGreen: "\x1b[42m",
  bgRed: "\x1b[41m",
  bgYellow: "\x1b[43m",
};

const bold = (s) => `${C.bold}${s}${C.reset}`;
const green = (s) => `${C.green}${s}${C.reset}`;
const yellow = (s) => `${C.yellow}${s}${C.reset}`;
const cyan = (s) => `${C.cyan}${s}${C.reset}`;
const red = (s) => `${C.red}${s}${C.reset}`;
const magenta = (s) => `${C.magenta}${s}${C.reset}`;
const dim = (s) => `${C.dim}${s}${C.reset}`;
const blue = (s) => `${C.blue}${s}${C.reset}`;

// ─── Arg Parsing ────────────────────────────────────────────────────────────

const args = process.argv.slice(2);
const keyword = args.find((a) => !a.startsWith("--"));
const showFull = args.includes("--full");
const opsOnly = args.includes("--ops-only");
const nodesOnly = args.includes("--nodes-only");
const jsonOutput = args.includes("--json");

if (!keyword) {
  console.error(red("ERROR: No keyword provided."));
  console.error(
    dim("Usage: node scripts/inspect_node.js <keyword> [--full] [--ops-only] [--nodes-only] [--json]")
  );
  console.error(dim("Example: node scripts/inspect_node.js slack"));
  process.exit(1);
}

// ─── Load Files ─────────────────────────────────────────────────────────────

function loadJSON(filePath, label) {
  if (!fs.existsSync(filePath)) {
    console.error(red(`ERROR: ${label} not found at: ${filePath}`));
    console.error(dim("Run normalize_registry.js and build_operation_index.js first."));
    process.exit(1);
  }
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf-8"));
  } catch (e) {
    console.error(red(`ERROR: Failed to parse ${label}: ${e.message}`));
    process.exit(1);
  }
}

const normalizedRegistry = loadJSON(NORMALIZED_PATH, "Normalized Registry");
const operationIndex = loadJSON(OPERATION_INDEX_PATH, "Operation Index");

// ─── Search Logic ────────────────────────────────────────────────────────────

const kw = keyword.toLowerCase();

/**
 * Match a node from the normalized registry against the keyword.
 * Checks: node_name, display_name, description, node_type, search_text
 */
function matchesNode(node) {
  return (
    (node.node_name || "").toLowerCase().includes(kw) ||
    (node.display_name || "").toLowerCase().includes(kw) ||
    (node.description || "").toLowerCase().includes(kw) ||
    (node.node_type || "").toLowerCase().includes(kw) ||
    (node.search_text || "").toLowerCase().includes(kw)
  );
}

/**
 * Match an operation from the operation index against the keyword.
 * Checks: node_name, display_name, resource, operation, action, search_text
 */
function matchesOp(op) {
  return (
    (op.node_name || "").toLowerCase().includes(kw) ||
    (op.display_name || "").toLowerCase().includes(kw) ||
    (op.resource || "").toLowerCase().includes(kw) ||
    (op.resource_name || "").toLowerCase().includes(kw) ||
    (op.operation || "").toLowerCase().includes(kw) ||
    (op.operation_name || "").toLowerCase().includes(kw) ||
    (op.action || "").toLowerCase().includes(kw) ||
    (op.search_text || "").toLowerCase().includes(kw)
  );
}

const matchedNodes = (normalizedRegistry.nodes || []).filter(matchesNode);
const matchedOps = (operationIndex.operations || []).filter(matchesOp);

// ─── JSON output mode ────────────────────────────────────────────────────────

if (jsonOutput) {
  console.log(
    JSON.stringify(
      {
        keyword,
        normalized_matches: matchedNodes.length,
        operation_matches: matchedOps.length,
        nodes: matchedNodes,
        operations: matchedOps,
      },
      null,
      2
    )
  );
  process.exit(0);
}

// ─── Pretty Print Helpers ────────────────────────────────────────────────────

function separator(char = "─", len = 80) {
  return dim(char.repeat(len));
}

function qualityBadge(node) {
  const issues = node.issues || [];
  if (!node.is_valid_for_generation) return red("[INVALID]");
  if (issues.length > 0) return yellow(`[WARN: ${issues.length} issue(s)]`);
  return green("[VALID]");
}

function credentialsBadge(creds) {
  if (!creds || creds.length === 0) return dim("none");
  return creds.map((c) => cyan(typeof c === "string" ? c : c.name || JSON.stringify(c))).join(", ");
}

function inputsOutputsBadge(val) {
  if (!val) return dim("?");
  if (Array.isArray(val)) return val.map((v) => green(v)).join(", ") || dim("[]");
  if (typeof val === "object") {
    const norm = val.normalized || [];
    const isDynamic = val.dynamic;
    const base = norm.map((v) => green(v)).join(", ") || dim("[]");
    return isDynamic ? base + yellow(" (dynamic)") : base;
  }
  return String(val);
}

function requiredFieldsBadge(fields) {
  if (!fields || fields.length === 0) return dim("none");
  return fields.map((f) => {
    const name = typeof f === "string" ? f : f.name || JSON.stringify(f);
    return magenta(name);
  }).join(", ");
}

function printNodeSummary(node, index) {
  console.log();
  console.log(separator());
  console.log(
    `  ${bold(cyan(`NODE ${index + 1}`))}  ${bold(node.display_name || node.node_name)}  ${qualityBadge(node)}`
  );
  console.log(separator());
  console.log(`  ${dim("node_type:")}      ${yellow(node.node_type || "?")}`);
  console.log(`  ${dim("node_name:")}      ${node.node_name || "?"}`);
  console.log(`  ${dim("versions:")}       ${(node.versions || [node.default_version]).join(", ")}  ${dim("(default: " + node.default_version + ")")}`);
  console.log(`  ${dim("group:")}          ${(node.group || []).join(", ") || dim("?")}`);
  console.log(`  ${dim("inputs:")}         ${inputsOutputsBadge(node.inputs)}`);
  console.log(`  ${dim("outputs:")}        ${inputsOutputsBadge(node.outputs)}`);
  console.log(`  ${dim("credentials:")}    ${credentialsBadge(node.credentials)}`);
  console.log(`  ${dim("description:")}    ${(node.description || "").substring(0, 120)}${node.description && node.description.length > 120 ? "…" : ""}`);

  // Resources and operations
  const resources = node.resources || [];
  const operations = node.operations || [];
  if (resources.length > 0) {
    console.log(`  ${dim("resources:")}      ${resources.map((r) => blue(r)).join(", ")}`);
  }
  if (operations.length > 0) {
    console.log(`  ${dim("operations:")}     ${operations.map((o) => blue(o)).join(", ")}`);
  }

  // Required fields
  const reqFields = node.required_fields || [];
  console.log(`  ${dim("required_fields:")} ${requiredFieldsBadge(reqFields)}`);

  // Search text
  if (node.search_text) {
    const st = node.search_text.substring(0, 100);
    console.log(`  ${dim("search_text:")}    ${dim(st)}${node.search_text.length > 100 ? dim("…") : ""}`);
  }

  // Issues
  const issues = node.issues || [];
  if (issues.length > 0) {
    console.log(`  ${dim("issues:")}`);
    issues.forEach((iss) => console.log(`    ${red("⚠")}  ${red(iss)}`));
  }

  // Properties (only with --full)
  if (showFull) {
    const props = node.properties || [];
    console.log(`  ${dim("properties:")}     ${props.length} fields`);
    if (props.length > 0) {
      console.log();
      props.slice(0, 20).forEach((p) => {
        const name = p.name || "?";
        const type = p.type || "?";
        const required = p.required ? red(" [required]") : "";
        const defaultVal = p.default !== undefined ? dim(` default=${JSON.stringify(p.default)}`) : "";
        console.log(`    ${magenta(name)} ${dim("(")}${cyan(type)}${dim(")")}${required}${defaultVal}`);
      });
      if (props.length > 20) {
        console.log(dim(`    ... and ${props.length - 20} more properties (use --full to see all)`));
      }
    }
  } else {
    const props = node.properties || [];
    console.log(`  ${dim("properties:")}     ${props.length} fields ${dim("(use --full to expand)")}`);
  }
}

function printOperationRow(op, index) {
  const resource = op.resource ? blue(op.resource_name || op.resource) : dim("(no resource)");
  const operation = op.operation ? green(op.operation_name || op.operation) : dim("(no operation)");
  const action = op.action ? `  ${dim("→")} ${op.action}` : "";
  const reqFields = (op.required_fields || []).map((f) => {
    return typeof f === "string" ? magenta(f) : magenta(f.name || JSON.stringify(f));
  }).join(", ") || dim("none");
  const creds = (op.credentials || []).map((c) => cyan(typeof c === "string" ? c : c.name || c)).join(", ") || dim("none");

  console.log(
    `  ${dim(String(index + 1).padStart(4, " "))}  ` +
    `${bold(op.display_name || op.node_name).padEnd(28)}  ` +
    `${resource.padEnd(20)}  ` +
    `${operation.padEnd(24)}  ` +
    `${dim("req:")} ${reqFields}`
  );
  if (action) console.log(`         ${dim("action:")} ${action}`);
  if (creds !== dim("none")) console.log(`         ${dim("creds:")}  ${creds}`);
}

// ─── Inspection Quality Report ───────────────────────────────────────────────

function qualityReport(nodes, ops) {
  const valid = nodes.filter((n) => n.is_valid_for_generation).length;
  const invalid = nodes.filter((n) => !n.is_valid_for_generation).length;
  const withCreds = nodes.filter((n) => (n.credentials || []).length > 0).length;
  const withRequiredFields = nodes.filter((n) => (n.required_fields || []).length > 0).length;
  const withResources = nodes.filter((n) => (n.resources || []).length > 0).length;
  const opsWithRequiredFields = ops.filter((o) => (o.required_fields || []).length > 0).length;

  console.log();
  console.log(separator("═"));
  console.log(`  ${bold("QUALITY REPORT")}  ${bold(cyan(`keyword: "${keyword}"`))}`);
  console.log(separator("═"));
  console.log();
  console.log(`  ${bold("Normalized Registry Matches:")}   ${bold(String(nodes.length))}`);
  console.log(`    ${green("✔")} Valid for generation:    ${green(String(valid))}`);
  console.log(`    ${red("✘")} Invalid / skipped:       ${invalid > 0 ? red(String(invalid)) : dim("0")}`);
  console.log(`    ${cyan("•")} With credentials:        ${withCreds > 0 ? cyan(String(withCreds)) : dim("0")}`);
  console.log(`    ${magenta("•")} With required_fields:    ${withRequiredFields > 0 ? magenta(String(withRequiredFields)) : dim("0")}`);
  console.log(`    ${blue("•")} With resources:          ${withResources > 0 ? blue(String(withResources)) : dim("0")}`);
  console.log();
  console.log(`  ${bold("Operation Index Matches:")}       ${bold(String(ops.length))}`);
  console.log(`    ${magenta("•")} Ops with required_fields: ${opsWithRequiredFields > 0 ? magenta(String(opsWithRequiredFields)) : dim("0")}`);
  console.log();

  // Readiness assessment
  const isReady = valid > 0 && ops.length > 0;
  if (isReady) {
    console.log(`  ${green("✔ READY")}  ${green(`"${keyword}" is discoverable and usable by the agent.`)}`);
  } else if (valid > 0 && ops.length === 0) {
    console.log(`  ${yellow("⚠ PARTIAL")}  ${yellow("Node found in registry but no operations indexed. May be a trigger or simple node.")}`);
  } else if (nodes.length > 0 && valid === 0) {
    console.log(`  ${red("✘ INVALID")}  ${red("Node found but marked invalid for generation. Check issues above.")}`);
  } else {
    console.log(`  ${red("✘ NOT FOUND")}  ${red(`No nodes or operations matched "${keyword}". Check if the package is installed.`)}`);
    console.log(`  ${dim("→ Fallback: the agent should use HTTP Request node for this integration.")}`);
  }

  console.log();
  console.log(separator("═"));
}

// ─── Main Output ─────────────────────────────────────────────────────────────

console.log();
console.log(bold(`${"═".repeat(80)}`));
console.log(bold(`  n8n Registry Inspector  —  keyword: "${keyword}"`));
console.log(bold(`${"═".repeat(80)}`));
console.log(
  dim(`  Normalized registry: ${normalizedRegistry.normalized_node_count || "?"} nodes  |  `) +
  dim(`Operation index: ${operationIndex.operation_count || "?"} operations`)
);

// ─── Section 1: Normalized Registry ─────────────────────────────────────────

if (!opsOnly) {
  console.log();
  console.log(bold(blue(`▶ SECTION 1 — Normalized Registry  (${matchedNodes.length} match(es))`)));

  if (matchedNodes.length === 0) {
    console.log(red(`  No nodes matched "${keyword}" in the normalized registry.`));
    console.log(dim(`  → Fallback: the agent should use HTTP Request node for "${keyword}".`));
  } else {
    matchedNodes.forEach((node, i) => printNodeSummary(node, i));
  }
}

// ─── Section 2: Operation Index ──────────────────────────────────────────────

if (!nodesOnly) {
  console.log();
  console.log(bold(blue(`▶ SECTION 2 — Operation Index  (${matchedOps.length} match(es))`)));

  if (matchedOps.length === 0) {
    console.log(red(`  No operations matched "${keyword}" in the operation index.`));
  } else {
    console.log(dim(`\n  ${"#".padStart(4)}  ${"Node".padEnd(28)}  ${"Resource".padEnd(20)}  ${"Operation".padEnd(24)}  Required Fields`));
    console.log(dim(`  ${"─".repeat(4)}  ${"─".repeat(28)}  ${"─".repeat(20)}  ${"─".repeat(24)}  ${"─".repeat(20)}`));
    matchedOps.forEach((op, i) => printOperationRow(op, i));
  }
}

// ─── Quality Report ──────────────────────────────────────────────────────────

qualityReport(matchedNodes, matchedOps);