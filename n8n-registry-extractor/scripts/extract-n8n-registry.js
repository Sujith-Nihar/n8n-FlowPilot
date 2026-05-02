const fs = require("fs");
const path = require("path");

const nodeModulesPath = path.join(process.cwd(), "node_modules");

function walk(dir, matcher, results = []) {
  if (!fs.existsSync(dir)) return results;

  for (const item of fs.readdirSync(dir)) {
    const fullPath = path.join(dir, item);
    const stat = fs.statSync(fullPath);

    if (stat.isDirectory()) {
      walk(fullPath, matcher, results);
    } else if (matcher(fullPath)) {
      results.push(fullPath);
    }
  }

  return results;
}

function findNodePackages() {
  const packages = [];

  for (const pkg of fs.readdirSync(nodeModulesPath)) {
    if (pkg === "n8n-nodes-base" || pkg.startsWith("n8n-nodes-")) {
      packages.push(path.join(nodeModulesPath, pkg));
    }

    // Scoped packages support: @scope/n8n-nodes-example
    if (pkg.startsWith("@")) {
      const scopePath = path.join(nodeModulesPath, pkg);
      if (!fs.statSync(scopePath).isDirectory()) continue;

      for (const scopedPkg of fs.readdirSync(scopePath)) {
        if (scopedPkg.startsWith("n8n-nodes-")) {
          packages.push(path.join(scopePath, scopedPkg));
        }
      }
    }
  }

  return packages;
}

function extractNodeDescription(filePath, packageName) {
  try {
    const mod = require(filePath);

    for (const exportKey of Object.keys(mod)) {
      const ExportedClass = mod[exportKey];

      if (typeof ExportedClass !== "function") continue;

      const instance = new ExportedClass();

      if (!instance.description) continue;

      const d = instance.description;

      return {
        source_package: packageName,
        source_file: filePath,
        class_name: exportKey,
        node_type: `${packageName}.${d.name}`,
        name: d.name,
        display_name: d.displayName,
        description: d.description,
        version: d.version,
        group: d.group,
        inputs: d.inputs,
        outputs: d.outputs,
        credentials: d.credentials || [],
        properties: d.properties || [],
        defaults: d.defaults || {},
        usable_as_tool: d.usableAsTool || false,
      };
    }
  } catch (error) {
    return {
      source_package: packageName,
      source_file: filePath,
      error: error.message,
    };
  }

  return null;
}

function extractCredentialDescription(filePath, packageName) {
  try {
    const mod = require(filePath);

    for (const exportKey of Object.keys(mod)) {
      const ExportedClass = mod[exportKey];

      if (typeof ExportedClass !== "function") continue;

      const instance = new ExportedClass();

      if (!instance.name || !instance.properties) continue;

      return {
        source_package: packageName,
        source_file: filePath,
        class_name: exportKey,
        name: instance.name,
        display_name: instance.displayName,
        documentation_url: instance.documentationUrl,
        properties: instance.properties || [],
        authenticate: instance.authenticate || null,
        test: instance.test || null,
      };
    }
  } catch (error) {
    return {
      source_package: packageName,
      source_file: filePath,
      error: error.message,
    };
  }

  return null;
}

function main() {
  const packages = findNodePackages();

  const nodes = [];
  const credentials = [];
  const errors = [];

  for (const pkgPath of packages) {
    const packageJsonPath = path.join(pkgPath, "package.json");
    const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, "utf8"));
    const packageName = packageJson.name;

    const distPath = path.join(pkgPath, "dist");

    const nodeFiles = walk(distPath, (file) => file.endsWith(".node.js"));
    const credentialFiles = walk(distPath, (file) =>
      file.endsWith(".credentials.js")
    );

    for (const file of nodeFiles) {
      const extracted = extractNodeDescription(file, packageName);

      if (!extracted) continue;

      if (extracted.error) {
        errors.push(extracted);
      } else {
        nodes.push(extracted);
      }
    }

    for (const file of credentialFiles) {
      const extracted = extractCredentialDescription(file, packageName);

      if (!extracted) continue;

      if (extracted.error) {
        errors.push(extracted);
      } else {
        credentials.push(extracted);
      }
    }
  }

  const output = {
    generated_at: new Date().toISOString(),
    node_count: nodes.length,
    credential_count: credentials.length,
    error_count: errors.length,
    nodes,
    credentials,
    errors,
  };

  fs.writeFileSync(
    path.join(process.cwd(), "n8n_registry.json"),
    JSON.stringify(output, null, 2)
  );

  console.log(`Nodes extracted: ${nodes.length}`);
  console.log(`Credentials extracted: ${credentials.length}`);
  console.log(`Errors: ${errors.length}`);
  console.log("Saved to n8n_registry.json");
}

main();