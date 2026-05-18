import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { imagesApi } from "@/api/images";
import { jobsApi } from "@/api/jobs";
import type { GeoImage } from "@/types";
import {
  Upload, CheckCircle, ChevronRight, Loader2, ImageIcon, Settings2, Play, Sparkles,
} from "lucide-react";
import clsx from "clsx";

type Step = "upload" | "params" | "running" | "done";

const STEPS: { key: Step; label: string; icon: any }[] = [
  { key: "upload", label: "Görüntü Yükle", icon: Upload },
  { key: "params", label: "Parametre Ayarla", icon: Settings2 },
  { key: "running", label: "Analiz", icon: Play },
  { key: "done", label: "Sonuç", icon: Sparkles },
];

function stepIndex(s: Step) { return STEPS.findIndex((x) => x.key === s); }

function DropZone({
  role, image, onFile, uploading,
}: { role: "before" | "after"; image: GeoImage | null; onFile: (f: File) => void; uploading: boolean }) {
  const [drag, setDrag] = useState(false);
  const title = role === "before" ? "Önceki Görüntü" : "Sonraki Görüntü";
  const sub = role === "before" ? "T₀ — değişimden önce" : "T₁ — değişimden sonra";

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDrag(false);
        const f = e.dataTransfer.files?.[0];
        if (f) onFile(f);
      }}
      className={clsx(
        "card relative overflow-hidden transition-all",
        drag && "border-accent shadow-glow scale-[1.01]",
      )}
    >
      <div className="absolute top-3 left-3 z-10">
        <span className="badge bg-bg-elev border border-border text-text-muted">
          {role.toUpperCase()}
        </span>
      </div>

      <div className="p-6 min-h-[180px] flex flex-col items-center justify-center text-center">
        {image ? (
          <>
            <div className="w-12 h-12 rounded-full bg-accent-green/15 border border-accent-green/40
                            flex items-center justify-center mb-3">
              <CheckCircle size={20} className="text-accent-green" />
            </div>
            <div className="text-sm font-medium text-text-primary">{image.filename}</div>
            <div className="text-[11px] text-text-muted mt-1 font-mono">
              {(image.size_bytes / 1024 / 1024).toFixed(1)} MB · {image.format}
              {image.crs && ` · ${image.crs}`}
            </div>
            <label className="mt-3 text-[11px] text-accent hover:text-accent-green cursor-pointer underline">
              Değiştir
              <input
                type="file"
                accept=".jpg,.jpeg,.png,.tif,.tiff,.jp2"
                className="hidden"
                disabled={uploading}
                onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); }}
              />
            </label>
          </>
        ) : (
          <label className="cursor-pointer w-full flex flex-col items-center">
            <div className="w-12 h-12 rounded-full bg-bg-elev border border-border
                            flex items-center justify-center mb-3">
              <ImageIcon size={20} className="text-text-muted" />
            </div>
            <div className="text-sm font-semibold text-text-primary">{title}</div>
            <div className="text-[11px] text-text-muted mt-1">{sub}</div>
            <div className="text-[10px] text-text-subtle mt-3 font-mono">
              JPG · PNG · GeoTIFF · JP2 — max 500 MB
            </div>
            <div className="mt-3 btn-secondary text-xs">
              {uploading ? <><Loader2 size={12} className="animate-spin" /> Yükleniyor</> : <><Upload size={12} /> Dosya Seç</>}
            </div>
            <input
              type="file"
              accept=".jpg,.jpeg,.png,.tif,.tiff,.jp2"
              className="hidden"
              disabled={uploading}
              onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); }}
            />
          </label>
        )}
      </div>
    </div>
  );
}

export default function NewAnalysis() {
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>("upload");
  const [beforeImage, setBeforeImage] = useState<GeoImage | null>(null);
  const [afterImage, setAfterImage] = useState<GeoImage | null>(null);
  const [confidence, setConfidence] = useState(0.65);
  const [minArea, setMinArea] = useState(25);
  const [model, setModel] = useState("classical-cv-sam");
  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleUpload = useCallback(
    async (file: File, role: "before" | "after") => {
      setUploading(true);
      try {
        const img = await imagesApi.upload(file);
        if (role === "before") setBeforeImage(img); else setAfterImage(img);
        toast.success(`${role === "before" ? "Önceki" : "Sonraki"} görüntü yüklendi`);
      } catch (err: any) {
        toast.error(err?.response?.data?.error?.message || "Yükleme başarısız");
      } finally {
        setUploading(false);
      }
    },
    []
  );

  async function startAnalysis() {
    if (!beforeImage || !afterImage) return;
    setSubmitting(true);
    try {
      const job = await jobsApi.create({
        before_image_id: beforeImage.id,
        after_image_id: afterImage.id,
        confidence_threshold: confidence,
        min_area_m2: minArea,
      });
      toast.success("Analiz başlatıldı");
      navigate(`/map/${job.id}`);
    } catch (err: any) {
      toast.error(err?.response?.data?.error?.message || "Analiz başlatılamadı");
    } finally {
      setSubmitting(false);
    }
  }

  const curr = stepIndex(step);

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* Stepper */}
      <div className="mb-8">
        <h1 className="text-xl font-bold text-text-primary">Yeni Analiz</h1>
        <p className="text-text-muted text-sm mt-1">
          İki tarihli görüntüyü karşılaştır, değişimleri otomatik tespit et.
        </p>

        <div className="mt-6 flex items-center gap-2">
          {STEPS.map((s, i) => {
            const Icon = s.icon;
            const active = i === curr;
            const done = i < curr;
            return (
              <div key={s.key} className="flex items-center gap-2 flex-1">
                <div
                  className={clsx(
                    "flex items-center gap-2 px-3 py-2 rounded border w-full",
                    active && "bg-accent/10 border-accent/50 text-accent",
                    done && "bg-cat-yeni/10 border-cat-yeni/40 text-cat-yeni",
                    !active && !done && "bg-bg-card border-border text-text-subtle"
                  )}
                >
                  <div className={clsx(
                    "w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold",
                    active && "bg-accent text-bg-base",
                    done && "bg-cat-yeni text-bg-base",
                    !active && !done && "bg-bg-elev"
                  )}>
                    {done ? <CheckCircle size={12} /> : <Icon size={12} />}
                  </div>
                  <span className="text-xs font-medium uppercase tracking-wide">{s.label}</span>
                </div>
                {i < STEPS.length - 1 && (
                  <ChevronRight size={14} className="text-text-subtle flex-shrink-0" />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Step body */}
      {step === "upload" && (
        <div className="space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            <DropZone role="before" image={beforeImage} onFile={(f) => handleUpload(f, "before")} uploading={uploading} />
            <DropZone role="after"  image={afterImage}  onFile={(f) => handleUpload(f, "after")}  uploading={uploading} />
          </div>

          <div className="flex justify-end">
            <button
              onClick={() => setStep("params")}
              disabled={!beforeImage || !afterImage}
              className="btn-primary"
            >
              Devam Et <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}

      {step === "params" && (
        <div className="card p-6 space-y-6">
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="label-sm">Güven Eşiği</label>
              <span className="text-accent font-mono text-sm">%{Math.round(confidence * 100)}</span>
            </div>
            <input
              type="range"
              min={0.50}
              max={0.95}
              step={0.01}
              value={confidence}
              onChange={(e) => setConfidence(parseFloat(e.target.value))}
              className="w-full accent-accent"
            />
            <div className="flex justify-between text-[10px] text-text-subtle mt-1 font-mono">
              <span>%50 (yüksek hassasiyet)</span>
              <span>%95 (yüksek kesinlik)</span>
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="label-sm">Minimum Değişim Alanı</label>
              <span className="text-accent font-mono text-sm">{minArea} m²</span>
            </div>
            <input
              type="number"
              min={25}
              max={500}
              step={5}
              value={minArea}
              onChange={(e) => setMinArea(Math.max(25, Math.min(500, parseInt(e.target.value) || 25)))}
              className="input w-full"
            />
            <p className="text-[10px] text-text-subtle mt-1">
              Bu eşiğin altındaki bölgeler gürültü kabul edilir (25–500 m²)
            </p>
          </div>

          <div>
            <label className="label-sm mb-2 block">Tespit Modeli</label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="input w-full"
            >
              <option value="classical-cv-sam">Klasik CV + SAM rafine (önerilen)</option>
              <option value="classical-cv">Yalnız Klasik CV (hızlı)</option>
              <option value="yolo-sam">YOLOv8 + SAM (yüklü model varsa)</option>
            </select>
            <p className="text-[10px] text-text-subtle mt-1">
              SAM modeli yüklü değilse otomatik olarak klasik CV'ye düşülür.
            </p>
          </div>

          <div className="flex gap-3 pt-2">
            <button onClick={() => setStep("upload")} className="btn-secondary flex-1">
              Geri
            </button>
            <button
              onClick={startAnalysis}
              disabled={submitting}
              className="btn-primary flex-1"
            >
              {submitting ? <><Loader2 size={14} className="animate-spin" /> Başlatılıyor</> : <><Play size={14} /> Analizi Başlat</>}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
