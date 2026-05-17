import { useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { imagesApi } from "@/api/images";
import { jobsApi } from "@/api/jobs";
import type { GeoImage } from "@/types";
import { Upload, CheckCircle, ArrowRight, Loader } from "lucide-react";
import clsx from "clsx";

type Step = "upload" | "params" | "running";

export default function NewAnalysis() {
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>("upload");
  const [beforeImage, setBeforeImage] = useState<GeoImage | null>(null);
  const [afterImage, setAfterImage] = useState<GeoImage | null>(null);
  const [confidence, setConfidence] = useState(0.5);
  const [uploading, setUploading] = useState(false);

  async function handleUpload(file: File, role: "before" | "after") {
    setUploading(true);
    try {
      const img = await imagesApi.upload(file);
      if (role === "before") setBeforeImage(img);
      else setAfterImage(img);
      toast.success(`${role === "before" ? "Önceki" : "Sonraki"} görüntü yüklendi`);
    } catch (err: any) {
      toast.error(err?.response?.data?.error?.message || "Yükleme başarısız");
    } finally {
      setUploading(false);
    }
  }

  async function startAnalysis() {
    if (!beforeImage || !afterImage) return;
    try {
      const job = await jobsApi.create({
        before_image_id: beforeImage.id,
        after_image_id: afterImage.id,
        confidence_threshold: confidence,
      });
      toast.success("Analiz başlatıldı!");
      navigate(`/map/${job.id}`);
    } catch (err: any) {
      toast.error(err?.response?.data?.error?.message || "Analiz başlatılamadı");
    }
  }

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Yeni Analiz</h1>
      <p className="text-gray-500 text-sm mb-8">Adım adım görüntü çifti yükleyin ve analizi başlatın.</p>

      {/* Steps indicator */}
      <div className="flex items-center gap-2 mb-10">
        {(["upload", "params"] as Step[]).map((s, i) => (
          <div key={s} className="flex items-center gap-2">
            <div className={clsx(
              "w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold",
              step === s || (step === "running" && i < 2)
                ? "bg-primary-600 text-white"
                : "bg-gray-200 text-gray-500"
            )}>
              {i + 1}
            </div>
            <span className="text-sm text-gray-600">{s === "upload" ? "Görüntü Yükle" : "Parametreler"}</span>
            {i < 1 && <ArrowRight size={14} className="text-gray-400" />}
          </div>
        ))}
      </div>

      {step === "upload" && (
        <div className="space-y-6">
          {(["before", "after"] as const).map((role) => {
            const img = role === "before" ? beforeImage : afterImage;
            return (
              <div key={role} className="bg-white rounded-xl shadow p-6">
                <h3 className="font-semibold mb-3 text-gray-800">
                  {role === "before" ? "Önceki Görüntü (Before)" : "Sonraki Görüntü (After)"}
                </h3>
                {img ? (
                  <div className="flex items-center gap-3 text-green-700">
                    <CheckCircle size={20} />
                    <span className="text-sm">{img.filename} ({(img.size_bytes / 1024 / 1024).toFixed(1)} MB)</span>
                  </div>
                ) : (
                  <label className="border-2 border-dashed border-gray-300 rounded-lg p-8 flex flex-col items-center cursor-pointer hover:border-primary-400 transition-colors">
                    <Upload size={28} className="text-gray-400 mb-2" />
                    <span className="text-sm text-gray-500">JPEG, PNG, GeoTIFF, JP2 — max 500 MB</span>
                    <input
                      type="file"
                      accept=".jpg,.jpeg,.png,.tif,.tiff,.jp2"
                      className="hidden"
                      disabled={uploading}
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f) handleUpload(f, role);
                      }}
                    />
                  </label>
                )}
              </div>
            );
          })}

          <button
            onClick={() => setStep("params")}
            disabled={!beforeImage || !afterImage}
            className="w-full bg-primary-600 hover:bg-primary-700 disabled:opacity-40 text-white py-2.5 rounded-lg font-medium transition-colors"
          >
            Devam Et
          </button>
        </div>
      )}

      {step === "params" && (
        <div className="bg-white rounded-xl shadow p-6 space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Güven Eşiği: {(confidence * 100).toFixed(0)}%
            </label>
            <input
              type="range"
              min={0.1}
              max={0.95}
              step={0.05}
              value={confidence}
              onChange={(e) => setConfidence(parseFloat(e.target.value))}
              className="w-full accent-primary-600"
            />
            <p className="text-xs text-gray-500 mt-1">
              Daha yüksek eşik = daha az ama daha güvenilir tespit
            </p>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => setStep("upload")}
              className="flex-1 border border-gray-300 py-2.5 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors"
            >
              Geri
            </button>
            <button
              onClick={startAnalysis}
              className="flex-1 bg-primary-600 hover:bg-primary-700 text-white py-2.5 rounded-lg text-sm font-medium transition-colors"
            >
              Analizi Başlat
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
