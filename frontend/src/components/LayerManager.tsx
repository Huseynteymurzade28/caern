import { Layers } from "lucide-react";

interface LayerManagerProps {
  visibleLayers: Set<string>;
  opacity: number;
  onToggle: (layer: string) => void;
  onOpacityChange: (val: number) => void;
}

const LAYERS = [
  { key: "YENI_YAPI", label: "Yeni Yapı", color: "#00ff88" },
  { key: "YIKIM", label: "Yıkım", color: "#ff4d6d" },
  { key: "VEJETASYON", label: "Vejetasyon", color: "#ffaa00" },
  { key: "YUZEY_DEG", label: "Yüzey Değ.", color: "#7aa6d6" },
];

export default function LayerManager({
  visibleLayers,
  opacity,
  onToggle,
  onOpacityChange,
}: LayerManagerProps) {
  return (
    <div className="card p-3">
      <div className="flex items-center gap-1.5 label-sm mb-3">
        <Layers size={11} />
        Katmanlar
      </div>

      <div className="space-y-1.5">
        {LAYERS.map(({ key, label, color }) => {
          const on = visibleLayers.has(key);
          return (
            <button
              key={key}
              onClick={() => onToggle(key)}
              className={`flex items-center w-full gap-2 px-2 py-1.5 rounded text-xs font-medium
                          border transition-colors ${
                            on
                              ? "bg-bg-elev border-border text-text-primary"
                              : "bg-transparent border-transparent text-text-subtle hover:bg-bg-elev/60"
                          }`}
            >
              <span
                className="w-2.5 h-2.5 rounded-sm flex-shrink-0"
                style={{
                  background: color,
                  boxShadow: on ? `0 0 8px ${color}80` : "none",
                  opacity: on ? 1 : 0.3,
                }}
              />
              <span className="flex-1 text-left">{label}</span>
              <span
                className={`w-7 h-3.5 rounded-full relative transition-colors ${
                  on ? "bg-accent/70" : "bg-bg-elev"
                }`}
              >
                <span
                  className={`absolute top-0.5 w-2.5 h-2.5 rounded-full bg-text-primary transition-all ${
                    on ? "left-3.5" : "left-0.5"
                  }`}
                />
              </span>
            </button>
          );
        })}
      </div>

      <div className="mt-3 pt-3 border-t border-border-subtle">
        <div className="flex justify-between label-sm mb-1">
          <span>Opaklık</span>
          <span className="text-text-primary">%{Math.round(opacity * 100)}</span>
        </div>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={opacity}
          onChange={(e) => onOpacityChange(parseFloat(e.target.value))}
          className="w-full accent-accent"
        />
      </div>
    </div>
  );
}
