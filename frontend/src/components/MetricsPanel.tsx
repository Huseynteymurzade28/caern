import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from "recharts";
import { FileDown, Activity, Layers, Gauge } from "lucide-react";
import type { MetricSummary, ChangeFeature } from "@/types";
import clsx from "clsx";

interface Props {
  jobStatus: string;
  metrics: MetricSummary | null;
  featureCount: number;
  detectionMode?: string | null;
  selectedFeature: ChangeFeature | null;
  onDownload: (format: "pdf" | "csv") => void;
  onClearSelection: () => void;
}

const CAT_COLORS: Record<string, string> = {
  YENI_YAPI: "#00ff88",
  YIKIM: "#ff4d6d",
  VEJETASYON: "#ffaa00",
  YUZEY_DEG: "#7aa6d6",
};

const CAT_LABEL: Record<string, string> = {
  YENI_YAPI: "Yeni Yapı",
  YIKIM: "Yıkım",
  VEJETASYON: "Vejetasyon",
  YUZEY_DEG: "Yüzey Değ.",
};

const STATUS_BADGE: Record<string, { label: string; cls: string }> = {
  completed: { label: "Tamamlandı", cls: "bg-cat-yeni/15 text-cat-yeni border-cat-yeni/40" },
  running:   { label: "Çalışıyor",  cls: "bg-accent/15 text-accent border-accent/40 animate-pulse" },
  aggregating: { label: "Birleştiriliyor", cls: "bg-accent/15 text-accent border-accent/40 animate-pulse" },
  queued:    { label: "Beklemede",  cls: "bg-cat-veje/15 text-cat-veje border-cat-veje/40" },
  failed:    { label: "Hata",       cls: "bg-cat-yikim/15 text-cat-yikim border-cat-yikim/40" },
  cancelled: { label: "İptal",      cls: "bg-text-subtle/15 text-text-subtle border-border" },
};

function MetricCard({
  label, value, sub, color,
}: { label: string; value: string; sub?: string; color: string }) {
  return (
    <div className="stat-card">
      <div className="label-sm flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full" style={{ background: color }} />
        {label}
      </div>
      <div className="text-lg font-semibold mt-1 text-text-primary leading-none">{value}</div>
      {sub && <div className="text-[10px] text-text-subtle mt-1">{sub}</div>}
    </div>
  );
}

export default function MetricsPanel({
  jobStatus, metrics, featureCount, detectionMode, selectedFeature,
  onDownload, onClearSelection,
}: Props) {
  const status = STATUS_BADGE[jobStatus] || STATUS_BADGE.queued;
  const byCat = metrics?.byCategory || ({} as any);

  const barData = Object.keys(CAT_LABEL).map((k) => ({
    name: CAT_LABEL[k],
    key: k,
    count: byCat[k]?.count || 0,
    color: CAT_COLORS[k],
  }));

  const totalConf = metrics?.avgConfidence ?? 0;
  const confPct = Math.round(totalConf * 100);

  const donutData = [
    { name: "Güven", value: confPct, color: "#00d4ff" },
    { name: "rest",  value: Math.max(0, 100 - confPct), color: "#1e3a5f" },
  ];

  return (
    <div className="flex flex-col gap-3 p-3 overflow-y-auto h-full">
      {/* Status */}
      <div className="flex items-center justify-between">
        <span className="label-sm">Durum</span>
        <span className={clsx("badge border", status.cls)}>{status.label}</span>
      </div>

      {/* Mini metric grid */}
      <div className="grid grid-cols-2 gap-2">
        <MetricCard
          label="Yeni Yapı"
          value={`${byCat.YENI_YAPI?.count || 0}`}
          sub={`${Math.round(byCat.YENI_YAPI?.areaM2 || 0).toLocaleString("tr-TR")} m²`}
          color={CAT_COLORS.YENI_YAPI}
        />
        <MetricCard
          label="Yıkım"
          value={`${byCat.YIKIM?.count || 0}`}
          sub={`${Math.round(byCat.YIKIM?.areaM2 || 0).toLocaleString("tr-TR")} m²`}
          color={CAT_COLORS.YIKIM}
        />
        <MetricCard
          label="Vejetasyon"
          value={`${byCat.VEJETASYON?.count || 0}`}
          sub={`${Math.round(byCat.VEJETASYON?.areaM2 || 0).toLocaleString("tr-TR")} m²`}
          color={CAT_COLORS.VEJETASYON}
        />
        <MetricCard
          label="Yüzey Değ."
          value={`${byCat.YUZEY_DEG?.count || 0}`}
          sub={`${Math.round(byCat.YUZEY_DEG?.areaM2 || 0).toLocaleString("tr-TR")} m²`}
          color={CAT_COLORS.YUZEY_DEG}
        />
      </div>

      {/* Bar chart */}
      <div className="card p-3">
        <div className="flex items-center gap-1.5 label-sm mb-2">
          <Layers size={11} /> Kategori Dağılımı
        </div>
        <div style={{ width: "100%", height: 120 }}>
          <ResponsiveContainer>
            <BarChart data={barData} margin={{ top: 4, right: 4, left: -28, bottom: 0 }}>
              <XAxis dataKey="name" tick={{ fill: "#5b6c87", fontSize: 9 }} axisLine={{ stroke: "#1e3a5f" }} />
              <YAxis allowDecimals={false} tick={{ fill: "#5b6c87", fontSize: 9 }} axisLine={{ stroke: "#1e3a5f" }} />
              <Tooltip
                cursor={{ fill: "rgba(0, 212, 255, 0.08)" }}
                contentStyle={{
                  background: "#0d1527",
                  border: "1px solid #1e3a5f",
                  borderRadius: 6,
                  fontSize: 11,
                  color: "#e7eef9",
                }}
              />
              <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                {barData.map((d) => <Cell key={d.key} fill={d.color} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Confidence gauge */}
      <div className="card p-3">
        <div className="flex items-center gap-1.5 label-sm mb-2">
          <Gauge size={11} /> Ortalama Güven
        </div>
        <div className="relative" style={{ width: "100%", height: 120 }}>
          <ResponsiveContainer>
            <PieChart>
              <Pie
                data={donutData}
                innerRadius={38}
                outerRadius={55}
                paddingAngle={0}
                startAngle={90}
                endAngle={-270}
                dataKey="value"
                stroke="none"
              >
                {donutData.map((d, i) => <Cell key={i} fill={d.color} />)}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <span className="text-2xl font-bold text-accent leading-none">%{confPct}</span>
            <span className="text-[9px] text-text-muted mt-1 uppercase tracking-wider">
              {featureCount} nesne
            </span>
          </div>
        </div>
      </div>

      {/* Reports */}
      <div className="card p-3">
        <div className="flex items-center gap-1.5 label-sm mb-2">
          <FileDown size={11} /> Rapor İndir
        </div>
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => onDownload("pdf")}
            className="btn bg-cat-yikim/15 border border-cat-yikim/40 text-cat-yikim
                       hover:bg-cat-yikim/25 hover:border-cat-yikim/70"
          >
            <FileDown size={13} /> PDF
          </button>
          <button
            onClick={() => onDownload("csv")}
            className="btn bg-cat-yeni/15 border border-cat-yeni/40 text-cat-yeni
                       hover:bg-cat-yeni/25 hover:border-cat-yeni/70"
          >
            <FileDown size={13} /> CSV
          </button>
        </div>
      </div>

      {/* Model info */}
      <div className="card p-3">
        <div className="flex items-center gap-1.5 label-sm mb-2">
          <Activity size={11} /> Tespit Bilgisi
        </div>
        <div className="text-[11px] space-y-1">
          <div className="flex justify-between">
            <span className="text-text-muted">Mod</span>
            <span className="font-mono text-text-primary">
              {detectionMode || metrics?.detection_mode || "—"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-muted">Toplam alan</span>
            <span className="font-mono text-text-primary">
              {((metrics?.totalAreaKm2 ?? 0)).toFixed(3)} km²
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-muted">Değişen alan</span>
            <span className="font-mono text-text-primary">
              {Math.round(metrics?.totalChangedAreaM2 ?? 0).toLocaleString("tr-TR")} m²
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-muted">Değişim oranı</span>
            <span className="font-mono text-accent">
              %{(metrics?.changePercent ?? 0).toFixed(2)}
            </span>
          </div>
        </div>
      </div>

      {/* Selected feature */}
      {selectedFeature && (
        <div className="card p-3 border-accent/40">
          <div className="flex items-start justify-between mb-2">
            <div className="label-sm">Seçili Nesne</div>
            <button
              onClick={onClearSelection}
              className="text-text-subtle hover:text-text-primary text-xs leading-none"
            >
              ×
            </button>
          </div>
          <div className="text-[11px] space-y-1">
            <div className="flex justify-between">
              <span className="text-text-muted">Kategori</span>
              <span
                className="font-semibold"
                style={{
                  color: CAT_COLORS[(selectedFeature.properties as any).category ||
                    (selectedFeature.properties as any).changeType] || "#7aa6d6",
                }}
              >
                {CAT_LABEL[(selectedFeature.properties as any).category ||
                  (selectedFeature.properties as any).changeType] ||
                  (selectedFeature.properties as any).category}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Alan</span>
              <span className="font-mono">
                {(selectedFeature.properties.areaM2 ?? 0).toFixed(1)} m²
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Güven</span>
              <span className="font-mono">%{(selectedFeature.properties.confidence * 100).toFixed(1)}</span>
            </div>
            {selectedFeature.properties.centroid && (
              <div className="pt-1 mt-1 border-t border-border-subtle text-[10px] text-text-subtle font-mono">
                {selectedFeature.properties.centroid[1].toFixed(5)},{" "}
                {selectedFeature.properties.centroid[0].toFixed(5)}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
