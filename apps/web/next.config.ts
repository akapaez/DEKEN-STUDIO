import type { NextConfig } from "next";

const config: NextConfig = {
  output: "standalone",
  // El monorepo comparte paquetes TS sin compilar.
  transpilePackages: ["@deken/brand", "@deken/shared", "@deken/video-compositions"],
  outputFileTracingRoot: new URL("../../", import.meta.url).pathname,
  poweredByHeader: false,
  reactStrictMode: true,
  typedRoutes: true,
};

export default config;
