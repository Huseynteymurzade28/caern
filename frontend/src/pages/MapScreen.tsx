import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { jobsApi } from "@/api/jobs";
import { reportsApi } from "@/api/reports";
import { useJobsStore } from "@/store/jobs";
import MapView from "@/components/MapView";
import LayerManager from "@/components/LayerManager";
import type { ChangeFeature } from "@/types";
import { FileDown, X } from "lucide-react";
import toast from "react-hot-toast";
import clsx from "clsx";

export default function MapScreen() {
  const { jobId } = useParams<{ jobId: string }>();
  const { progress, progressMsg, results, setProgress, setResults, setActiveJob } = useJobsStore();
  const [opacity, setOpacity] = useState(0.8);
  const [visibleLayers, setVisibleLayers] = useState(new Set(["new", "lost"]));
  const [selectedFeature, setSelectedFeature] = useState<ChangeFeature | null>(null);

  useEffect(() => {
    if (!jobId) return;
    setActiveJob(jobId);

    const es = jobsApi.streamProgress(
      jobId,
      (evt) => setProgress(evt.progress, evt.message),
      async () => {
        try {
          const fc = await jobsApi.getResults(jobId!);
          setResults(fc);
        } catch {}
      },
      () => toast.error("SSE bağlantısı kesildi")
    );
    return () => es.close();
  }, [jobId]);

  function toggleLayer(key: string) {
    setVisibleLayers((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  }

  async function downloadReport(format: "pdf" | "csv") {
    try {
      const report = await reportsApi.create(jobId!, format);
      const url = await reportsApi.getDownloadUrl(report.id);
      window.open(url, "_blank");
      toast.success(`${format.toUpperCase()} hazırlandı`);
    } catch {
      toast.error("Rapor oluşturulamadı");
    }
  }

  const handleFeatureClick = useCallback((feat: ChangeFeature) => {
    setSelectedFeature(feat);
  }, []);

  return (
    <div className="flex h-full">
      {/* Left Panel */}
      <div className="w-64 flex-shrink-0 bg-gray-50 border-r p-4 space-y-4 overflow-y-auto">
        <LayerManager
          visibleLayers={visibleLayers}
          opacity={opacity}
          onToggle={toggleLayer}
          onOpacityChange={setOpacity}
        />

        {results && (
          <div className="bg-white rounded-xl shadow p-4 space-y-2">
            <h3 className="font-semibold text-gray-800 text-sm uppercase tracking-wide">Rapor</h3>
            <button
              onClick={() => downloadReport("pdf")}
              className="flex items-center gap-2 w-full text-sm px-3 py-2 bg-red-50 hover:bg-red-100 text-red-700 rounded-lg transition-colors"
            >
              <FileDown size={15} /> PDF İndir
            </button>
            <button
              onClick={() => downloadReport("csv")}
              className="flex items-center gap-2 w-full text-sm px-3 py-2 bg-green-50 hover:bg-green-100 text-green-700 rounded-lg transition-colors"
            >
              <FileDown size={15} /> CSV İndir
            </button>
          </div>
        )}
      </div>

      {/* Map */}
      <div className="flex-1 relative">
        {progress < 100 && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[1000] bg-white rounded-xl shadow-lg p-4 min-w-64">
            <p className="text-xs text-gray-500 mb-1">{progressMsg || "İşleniyor..."}</p>
            <div className="bg-gray-200 rounded-full h-2">
              <div
                className="bg-primary-600 h-2 rounded-full transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-right text-xs text-gray-600 mt-1">{Math.round(progress)}%</p>
          </div>
        )}

        <MapView
          featureCollection={results}
          layerOpacity={opacity}
          visibleLayers={visibleLayers}
          onFeatureClick={handleFeatureClick}
        />
      </div>

      {/* Right Panel */}
      {results && (
        <div className="w-72 flex-shrink-0 bg-gray-50 border-l p-4 space-y-4 overflow-y-auto">
          <div className="bg-white rounded-xl shadow p-4">
            <h3 className="font-semibold text-gray-800 text-sm uppercase tracking-wide mb-3">Analiz Özeti</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Toplam tespit</span>
                <span className="font-medium">{results.features.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-green-600">Yeni</span>
                <span className="font-medium">{results.features.filter((f) => f.properties.changeType === "new").length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-red-600">Kaybolan</span>
                <span className="font-medium">{results.features.filter((f) => f.properties.changeType === "lost").length}</span>
              </div>
            </div>
          </div>

          {selectedFeature && (
            <div className="bg-white rounded-xl shadow p-4 relative">
              <button onClick={() => setSelectedFeature(null)} className="absolute top-2 right-2 text-gray-400 hover:text-gray-600">
                <X size={16} />
              </button>
              <h4 className="font-semibold text-sm mb-3">Seçili Nesne</h4>
              <dl className="space-y-1.5 text-xs">
                <div className="flex justify-between">
                  <dt className="text-gray-500">Sınıf</dt>
                  <dd className="font-medium">{selectedFeature.properties.classLabel}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">Değişim</dt>
                  <dd className={clsx("font-medium", selectedFeature.properties.changeType === "new" ? "text-green-600" : "text-red-600")}>
                    {selectedFeature.properties.changeType === "new" ? "Yeni" : "Kaybolan"}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">Güven</dt>
                  <dd className="font-medium">{(selectedFeature.properties.confidence * 100).toFixed(1)}%</dd>
                </div>
                {selectedFeature.properties.areaM2 && (
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Alan</dt>
                    <dd className="font-medium">{selectedFeature.properties.areaM2.toFixed(0)} m²</dd>
                  </div>
                )}
              </dl>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
