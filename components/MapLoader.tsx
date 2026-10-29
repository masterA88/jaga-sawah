"use client";

import dynamic from "next/dynamic";

// MapLibre needs the browser (WebGL), so the map never renders on the server.
const MapApp = dynamic(() => import("./MapApp"), {
  ssr: false,
  loading: () => <div className="p-6 text-sm text-neutral-500">Memuat peta...</div>,
});

export default function MapLoader() {
  return <MapApp />;
}
