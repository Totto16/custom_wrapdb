import fsAsync from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

function getFrontendRoot(script_file: string): string {
  const __dirname = path.dirname(__filename);

  if (script_file.endsWith(".ts")) {
    return path.join(__dirname, "..");
  }

  //NOTE the js is emitted into the same dir structure, but it might not
  return path.join(__dirname, "..");
}

async function moveFileWithReplacements(
  inFile: string,
  outFile: string,
  replacements: Record<string, string>,
): Promise<void> {
  const inContent = await fsAsync.readFile(inFile, {
    encoding: "utf-8",
  });

  let content = inContent;

  for (const [key, value] of Object.entries(replacements)) {
    const realKey = key.replaceAll("-", "_").toUpperCase();

    content = content.replace(`{{${realKey}}`, value);
  }

  await fsAsync.writeFile(outFile, content);
}

async function main(): Promise<void> {
  if (!process.argv[0]!.endsWith("node")) {
    throw new Error("Script can't be invoked standalone");
  }

  if (process.argv.length != 3) {
    throw new Error("Not the right amounts of arguments");
  }

  const table_html_file = process.argv[2]!;

  const table_html = await fsAsync.readFile(table_html_file, {
    encoding: "utf-8",
  });

  const frontendRoot = getFrontendRoot(process.argv[1]!);

  const inFile = path.join(frontendRoot, "static", "projects.html");

  const outFile = path.join(frontendRoot, "static", "Wrapdb-projects.html");

  await moveFileWithReplacements(inFile, outFile, {
    "html-table-here": table_html,
  });
}

void main();
