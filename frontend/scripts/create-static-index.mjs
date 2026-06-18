import { readdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";

const clientDir = "dist/client";
const assetsDir = join(clientDir, "assets");

const assets = await readdir(assetsDir);
const cssAssets = assets.filter((asset) => asset.endsWith(".css")).sort();
let entryAsset;

for (const asset of assets.filter((candidate) => candidate.endsWith(".js")).sort()) {
  const source = await readFile(join(assetsDir, asset), "utf8");
  if (source.includes("hydrateRoot(document")) {
    entryAsset = asset;
    break;
  }
}

if (!entryAsset) {
  throw new Error("Unable to find TanStack Start client entry asset.");
}

const cssLinks = cssAssets
  .map((asset) => `    <link rel="stylesheet" href="/assets/${asset}" />`)
  .join("\n");

await writeFile(
  join(clientDir, "index.html"),
  `<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>SentinelAI XDR</title>
${cssLinks}
  </head>
  <body class="bg-background text-foreground antialiased">
    <script type="module" src="/assets/${entryAsset}"></script>
  </body>
</html>
`,
);
