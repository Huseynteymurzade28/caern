import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import type { FeatureCollection, ChangeFeature } from "@/types";

interface MapViewProps {
  featureCollection: FeatureCollection | null;
  layerOpacity: number;
  visibleLayers: Set<string>;
  onFeatureClick: (feat: ChangeFeature) => void;
}

const CATEGORY_STYLES: Record<string, { fill: string; stroke: string; opacity: number }> = {
  YENI_YAPI:  { fill: "#00ff88", stroke: "#00ff88", opacity: 0.60 },
  YIKIM:      { fill: "#ff4d6d", stroke: "#ff4d6d", opacity: 0.60 },
  VEJETASYON: { fill: "#ffaa00", stroke: "#ffaa00", opacity: 0.50 },
  YUZEY_DEG:  { fill: "#7aa6d6", stroke: "#7aa6d6", opacity: 0.45 },
  // legacy
  new:  { fill: "#00ff88", stroke: "#00ff88", opacity: 0.60 },
  lost: { fill: "#ff4d6d", stroke: "#ff4d6d", opacity: 0.60 },
};

const CATEGORY_LABEL: Record<string, string> = {
  YENI_YAPI: "Yeni Yapı",
  YIKIM: "Yıkım",
  VEJETASYON: "Vejetasyon",
  YUZEY_DEG: "Yüzey Değişimi",
  new: "Yeni",
  lost: "Kaybolan",
};

function categoryOf(feat: ChangeFeature): string {
  const p = feat.properties as any;
  return p.category || p.changeType || "YUZEY_DEG";
}

export default function MapView({
  featureCollection,
  layerOpacity,
  visibleLayers,
  onFeatureClick,
}: MapViewProps) {
  const mapRef = useRef<L.Map | null>(null);
  const layersRef = useRef<L.GeoJSON | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = L.map(containerRef.current, {
      center: [39.9, 32.8],
      zoom: 7,
      preferCanvas: true,
      zoomControl: false,
      attributionControl: true,
    });

    // Dark basemap (CartoDB Dark Matter)
    L.tileLayer(
      "https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
      {
        attribution:
          '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> · © <a href="https://carto.com/">CARTO</a>',
        maxZoom: 20,
        subdomains: "abcd",
      }
    ).addTo(map);

    L.control.zoom({ position: "bottomright" }).addTo(map);
    L.control.scale({ position: "bottomleft", imperial: false, metric: true }).addTo(map);

    map.on("mousemove", (e: L.LeafletMouseEvent) => {
      setCoords({ lat: e.latlng.lat, lng: e.latlng.lng });
    });
    map.on("mouseout", () => setCoords(null));

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // GeoJSON layer
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !featureCollection) return;

    if (layersRef.current) {
      map.removeLayer(layersRef.current);
    }

    const geoLayer = L.geoJSON(featureCollection as any, {
      style: (feat) => {
        const cat = categoryOf(feat as ChangeFeature);
        const visible = visibleLayers.has(cat);
        const s = CATEGORY_STYLES[cat] || CATEGORY_STYLES.YUZEY_DEG;
        return {
          color: s.stroke,
          weight: 1.5,
          fillColor: s.fill,
          fillOpacity: visible ? layerOpacity * s.opacity : 0,
          opacity: visible ? layerOpacity * 0.9 : 0,
        };
      },
      onEachFeature: (feat, layer) => {
        const f = feat as ChangeFeature;
        const cat = categoryOf(f);
        const props = f.properties as any;
        const c = props.centroid || [null, null];
        const popup = `
          <div class="caern-popup">
            <div class="row"><span class="k">Kategori</span>
              <span class="v" style="color: ${CATEGORY_STYLES[cat]?.fill}">${CATEGORY_LABEL[cat] || cat}</span>
            </div>
            <div class="row"><span class="k">Alan</span>
              <span class="v">${(props.areaM2 || 0).toFixed(1)} m²</span>
            </div>
            <div class="row"><span class="k">Güven</span>
              <span class="v">%${(props.confidence * 100).toFixed(1)}</span>
            </div>
            ${c[0] != null ? `<div class="row"><span class="k">Konum</span>
              <span class="v" style="font-family: monospace; font-size: 11px">
                ${c[1].toFixed(5)}, ${c[0].toFixed(5)}
              </span></div>` : ""}
          </div>
        `;
        layer.bindPopup(popup, { className: "caern-popup-wrapper", maxWidth: 260 });
        layer.on("click", () => onFeatureClick(f));
      },
    }).addTo(map);

    layersRef.current = geoLayer;

    if (featureCollection.features.length > 0) {
      try {
        const b = geoLayer.getBounds();
        if (b.isValid()) map.fitBounds(b, { padding: [40, 40] });
      } catch {}
    }
  }, [featureCollection, layerOpacity, visibleLayers, onFeatureClick]);

  function toggleFullscreen() {
    const el: any = containerRef.current?.parentElement;
    if (!el) return;
    const doc: any = document;
    if (doc.fullscreenElement) {
      doc.exitFullscreen?.();
    } else {
      el.requestFullscreen?.();
    }
    setTimeout(() => mapRef.current?.invalidateSize(), 300);
  }

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full" />

      {/* Fullscreen */}
      <button
        onClick={toggleFullscreen}
        title="Tam ekran"
        className="absolute top-3 right-3 z-[1000] w-9 h-9 bg-bg-panel/90 border border-border rounded
                   flex items-center justify-center text-text-muted hover:text-accent
                   hover:border-accent/60 transition-colors"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M8 3H5a2 2 0 0 0-2 2v3" />
          <path d="M21 8V5a2 2 0 0 0-2-2h-3" />
          <path d="M3 16v3a2 2 0 0 0 2 2h3" />
          <path d="M16 21h3a2 2 0 0 0 2-2v-3" />
        </svg>
      </button>

      {/* Coordinate readout */}
      {coords && (
        <div className="absolute bottom-3 left-1/2 -translate-x-1/2 z-[1000]
                        bg-bg-panel/90 border border-border rounded px-3 py-1
                        text-[11px] font-mono text-text-muted">
          {coords.lat.toFixed(5)}, {coords.lng.toFixed(5)}
        </div>
      )}
    </div>
  );
}
