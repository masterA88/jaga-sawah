// MapLibre 6 resolves its worker next to its own module URL, which Turbopack chunks break.
// Serve the self-contained worker from /public and point setWorkerUrl at it (components/MapApp.tsx).
import { copyFileSync, mkdirSync } from "node:fs";

mkdirSync("public/maplibre", { recursive: true });
copyFileSync("node_modules/maplibre-gl/dist/maplibre-gl-worker.mjs", "public/maplibre/maplibre-gl-worker.mjs");
