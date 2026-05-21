import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { jobsApi } from "@/api/jobs";
import { reportsApi } from "@/api/reports";
import { useJobsStore } from "@/store/jobs";
import MapView from "@/components/MapView";
import LayerManager from "@/components/LayerManager";
import MetricsPanel from "@/components/MetricsPanel";
import type { ChangeFeature, MetricSummary } from "@/types";
import toast from "react-hot-toast";
import { Loader2 } from "lucide-react";

const PROGRESS_STEPS: { from: number; to: number; label: string }[] = [
  { from: 0,  to: 15, label: "Yüklendi" },
  { from: 15, to: 35, label: "Hizalandı" },
  { from: 35, to: 85, label: "Analiz Ediliyor" },
  { from: 85, to: 99, label: "Sonuçlar Yazılıyor" },
  { from: 99, to: 100, label: "Tamamlandı" },
];

const ALL_LAYERS = new Set(["YENI_YAPI", "YIKIM", "VEJETASYON", "YUZEY_DEG"]);

export default function MapScreen() {
  const { jobId } = useParams<{ jobId: string }>();
  const { progress, progressMsg, results, setProgress, setResults, setActiveJob } = useJobsStore();
  const [opacity, setOpacity] = useState(0.8);
  const [visibleLayers, setVisibleLayers] = useState<Set<string>>(ALL_LAYERS);
  const [selectedFeature, setSelectedFeature] = useState<ChangeFeature | null>(null);

  useEffect(() => {
    if (!jobId) return;
    setActiveJob(jobId);
    setSelectedFeature(null);

    let es: EventSource | null = null;
    let cancelled = false;

    (async () => {
      // Önce mevcut sonuçları getir — tamamlanmış analizler anında açılsın
      try {
        const fc = await jobsApi.getResults(jobId);
        if (cancelled) return;
        const status = fc?.metadata?.status;
        const isTerminal =
          status === "completed" || status === "failed" || status === "cancelled";

        if (fc?.features?.length || isTerminal) {
          setResults(fc);
          setProgress(
            100,
            status === "failed" ? "FAILED" :
            status === "cancelled" ? "CANCELLED" : "COMPLETED",
          );
        }

        // SSE'yi yalnızca devam eden analizler için aç
        if (!isTerminal) {
          es = jobsApi.streamProgress(
            jobId,
            (evt) => setProgress(evt.progress, evt.message),
            async () => {
              try {
                const updated = await jobsApi.getResults(jobId!);
                if (!cancelled) setResults(updated);
              } catch {}
            },
            () => {
              if (!cancelled) toast.error("SSE bağlantısı kesildi");
            },
          );
        }
      } catch {
        if (!cancelled) toast.error("Analiz sonuçları yüklenemedi");
      }
    })();

    return () => {
      cancelled = true;
      es?.close();
    };
  }, [jobId]);

  function toggleLayer(key: string) {
    setVisibleLayers((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  }

  async function downloadReport(format: "pdf" | "csv") {
    if (!jobId) return;
    const tid = toast.loading(`${format.toUpperCase()} oluşturuluyor…`);
    try {
      await reportsApi.streamDownload(jobId, format);
      toast.success(`${format.toUpperCase()} indirildi`, { id: tid });
    } catch (e: any) {
      toast.error(`Rapor oluşturulamadı: ${e?.message || "bilinmeyen"}`, { id: tid });
    }
  }

  const handleFeatureClick = useCallback((feat: ChangeFeature) => {
    setSelectedFeature(feat);
  }, []);

  const metrics: MetricSummary | null = (results?.metadata as any)?.metrics || null;
  const detectionMode: string | undefined = (results?.metadata as any)?.detectionMode || metrics?.detection_mode;
  const jobStatus = results?.metadata?.status || (progress >= 100 ? "completed" : "running");

  const currentStep = useMemo(
    () => PROGRESS_STEPS.find((s) => progress >= s.from && progress < s.to) || PROGRESS_STEPS[PROGRESS_STEPS.length - 1],
    [progress]
  );

  return (
    <div className="flex h-full">
      {/* SOL PANEL — 200px */}
      <aside className="w-[200px] flex-shrink-0 panel border-r flex flex-col overflow-y-auto">
        <div className="p-3 space-y-3 flex-1">
          <LayerManager
            visibleLayers={visibleLayers}
            opacity={opacity}
            onToggle={toggleLayer}
            onOpacityChange={setOpacity}
          />

          {/* Lejant */}
          <div className="card p-3">
            <div className="label-sm mb-2">Lejant</div>
            <div className="space-y-1 text-[11px]">
              {[
                { c: "#00ff88", k: "Yeni Yapı" },
                { c: "#ff4d6d", k: "Yıkım" },
                { c: "#ffaa00", k: "Vejetasyon" },
                { c: "#7aa6d6", k: "Yüzey Değ." },
              ].map((l) => (
                <div key={l.k} className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-sm" style={{ background: l.c }} />
                  <span className="text-text-muted">{l.k}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="border-t border-border-subtle p-3 text-[10px] font-mono text-text-subtle">
          <div className="label-sm mb-1">Analiz ID</div>
          <div className="break-all">{jobId?.slice(0, 18)}…</div>
        </div>
      </aside>

      {/* HARITA */}
      <div className="flex-1 relative bg-bg-base">
        {/* Progress overlay */}
        {progress < 100 && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[1000]
                          panel rounded-lg p-4 shadow-glow min-w-[360px]">
            <div className="flex items-center gap-2 mb-3">
              <Loader2 size={14} className="text-accent animate-spin" />
              <span className="text-xs uppercase tracking-wider text-accent">
                {currentStep.label}
              </span>
              <div className="flex-1" />
              <span className="text-xs font-mono text-text-primary">{Math.round(progress)}%</span>
            </div>

            <div className="bg-bg-base rounded-full h-1.5 overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${progress}%`,
                  background: "linear-gradient(90deg, #0099bb, #00d4ff, #00ff88)",
                  boxShadow: "0 0 8px rgba(0, 212, 255, 0.6)",
                }}
              />
            </div>

            {/* Step pills */}
            <div className="flex gap-1.5 mt-3">
              {PROGRESS_STEPS.map((s, i) => (
                <div
                  key={i}
                  className={`flex-1 h-1 rounded-full transition-colors ${
                    progress >= s.to
                      ? "bg-accent-green"
                      : progress >= s.from
                      ? "bg-accent animate-pulse"
                      : "bg-border-subtle"
                  }`}
                />
              ))}
            </div>

            {progressMsg && (
              <div className="text-[10px] text-text-subtle mt-2 font-mono truncate">
                › {progressMsg}
              </div>
            )}
          </div>
        )}

        <MapView
          featureCollection={results}
          layerOpacity={opacity}
          visibleLayers={visibleLayers}
          onFeatureClick={handleFeatureClick}
        />
      </div>

      {/* SAG PANEL — 300px */}
      <aside className="w-[300px] flex-shrink-0 panel border-l overflow-hidden">
        <MetricsPanel
          jobStatus={jobStatus}
          metrics={metrics}
          detectionMode={detectionMode}
          featureCount={results?.features.length || 0}
          selectedFeature={selectedFeature}
          onDownload={downloadReport}
          onClearSelection={() => setSelectedFeature(null)}
        />
      </aside>
    </div>
  );
}
