// Empaqueta los CLI del motor (TypeScript del monorepo incluido) en dist/.
import { build } from "esbuild";

const common = {
  bundle: true,
  platform: "node",
  format: "esm",
  target: "node22",
  packages: "external",
  outdir: "dist",
  banner: { js: "import { createRequire as __cr } from 'node:module'; const require = __cr(import.meta.url);" },
  logLevel: "warning",
};

// @deken/video-compositions es código fuente TS: se incluye en el bundle.
await build({
  ...common,
  entryPoints: ["src/cli.ts", "src/bundle.ts"],
  plugins: [
    {
      name: "bundle-workspace-sources",
      setup(b) {
        b.onResolve({ filter: /^@deken\/video-compositions/ }, () => ({ external: false }));
      },
    },
  ],
  packages: undefined,
  external: ["@remotion/*", "remotion", "react", "react-dom", "zod"],
});
