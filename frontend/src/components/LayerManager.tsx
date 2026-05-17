interface LayerManagerProps {
  visibleLayers: Set<string>;
  opacity: number;
  onToggle: (layer: string) => void;
  onOpacityChange: (val: number) => void;
}

const LAYERS = [
  { key: "new", label: "Yeni Nesneler", color: "#16a34a" },
  { key: "lost", label: "Kaybolan Nesneler", color: "#dc2626" },
];

export default function LayerManager({
  visibleLayers, opacity, onToggle, onOpacityChange,
}: LayerManagerProps) {
  return (
    <div className="bg-white rounded-xl shadow p-4 space-y-4">
      <h3 className="font-semibold text-gray-800 text-sm uppercase tracking-wide">Katmanlar</h3>
      {LAYERS.map(({ key, label, color }) => (
        <label key={key} className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={visibleLayers.has(key)}
            onChange={() => onToggle(key)}
            className="accent-blue-600 w-4 h-4"
          />
          <span
            className="w-3 h-3 rounded-full flex-shrink-0"
            style={{ backgroundColor: color }}
          />
          <span className="text-sm text-gray-700">{label}</span>
        </label>
      ))}
      <div>
        <label className="text-xs text-gray-500 block mb-1">Opaklık: {Math.round(opacity * 100)}%</label>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={opacity}
          onChange={(e) => onOpacityChange(parseFloat(e.target.value))}
          className="w-full accent-blue-600"
        />
      </div>
    </div>
  );
}
