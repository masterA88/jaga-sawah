import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  cacheComponents: true,
  // the live AI routes read the server-only LSD file and the candidate GeoJSON from disk
  outputFileTracingIncludes: {
    "/api/*": ["./data/**/*", "./public/data/*.geojson"],
  },
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
