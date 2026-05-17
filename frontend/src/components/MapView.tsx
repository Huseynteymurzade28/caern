import { useEffect, useRef } from "react";
import L from "leaflet";
import type { FeatureCollection, ChangeFeature } from "@/types";

interface MapViewProps {
  featureCollection: FeatureCollection | null;
  layerOpacity: number;
  visibleLayers: Set<string>;
  onFeatureClick: (feat: ChangeFeature) => void;
}

const COLORS = { new: "#16a34a", lost: "#dc2626" };

export default function MapView({
  featureCollection,
  layerOpacity,
  visibleLayers,
  onFeatureClick,
}: MapViewProps) {
  const mapRef = useRef<L.Map | null>(null);
  const layersRef = useRef<L.GeoJSON | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    mapRef.current = L.map(containerRef.current, {
      center: [39.9, 32.8],
      zoom: 7,
      preferCanvas: true,
    });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap contributors",
    }).addTo(mapRef.current);
    return () => {
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !featureCollection) return;

    if (layersRef.current) {
      map.removeLayer(layersRef.current);
    }

    const geoLayer = L.geoJSON(featureCollection as any, {
      style: (feat) => {
        const ct = (feat as any)?.properties?.changeType as "new" | "lost";
        const show = visibleLayers.has(ct);
        return {
          color: COLORS[ct] || "#888",
          weight: 2,
          fillOpacity: show ? layerOpacity * 0.6 : 0,
          opacity: show ? layerOpacity : 0,
        };
      },
      onEachFeature: (feat, layer) => {
        layer.on("click", () => onFeatureClick(feat as ChangeFeature));
      },
    }).addTo(map);

    layersRef.current = geoLayer;

    if (featureCollection.features.length > 0) {
      map.fitBounds(geoLayer.getBounds(), { padding: [20, 20] });
    }
  }, [featureCollection, layerOpacity, visibleLayers, onFeatureClick]);

  return <div ref={containerRef} className="h-full w-full" />;
}
