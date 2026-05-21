import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { apiClient } from "@/api/client";
import type { AnalysisJob } from "@/types";
import { format } from "date-fns";
import { tr } from "date-fns/locale";
import { Plus, ChevronRight, Activity, Clock, TrendingUp, Eye } from "lucide-react";
import clsx from "clsx";

const STATUS_COLORS: Record<string, string> = {
  completed: "bg-cat-yeni/15 text-cat-yeni border-cat-yeni/40",
  running:   "bg-accent/15 text-accent border-accent/40 animate-pulse",
  aggregating: "bg-accent/15 text-accent border-accent/40 animate-pulse",
  failed:    "bg-cat-yikim/15 text-cat-yikim border-cat-yikim/40",
  queued:    "bg-cat-veje/15 text-cat-veje border-cat-veje/40",
  cancelled: "bg-text-subtle/15 text-text-subtle border-border",
};

const STATUS_LABEL: Record<string, string> = {
  completed: "Tamamlandı",
  running: "Çalışıyor",
  aggregating: "Birleştiriliyor",
  failed: "Hata",
  queued: "Beklemede",
  cancelled: "İptal",
  created: "Oluşturuldu",
  validating: "Doğrulanıyor",
};

export default function Dashboard() {
  const navigate = useNavigate();
  const { data: jobs, isLoading } = useQuery<AnalysisJob[]>({
    queryKey: ["jobs"],
    queryFn: async () => {
      const { data } = await apiClient.get("/jobs");
      return data;
    },
    refetchInterval: 5000,
  });

  const total = jobs?.length || 0;
  const completed = jobs?.filter((j) => j.status === "completed").length || 0;
  const running = jobs?.filter((j) => ["running", "queued", "aggregating"].includes(j.status)).length || 0;

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Analiz İşleri</h1>
          <p className="text-text-muted text-sm mt-1">
            Son çalıştırılan değişim tespiti analizleri
          </p>
        </div>
        <button onClick={() => navigate("/analysis/new")} className="btn-primary">
          <Plus size={14} /> Yeni Analiz
        </button>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="card p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded bg-accent/15 border border-accent/30
                          flex items-center justify-center">
            <Activity size={18} className="text-accent" />
          </div>
          <div>
            <div className="label-sm">Toplam Analiz</div>
            <div className="text-xl font-bold text-text-primary">{total}</div>
          </div>
        </div>
        <div className="card p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded bg-cat-yeni/15 border border-cat-yeni/30
                          flex items-center justify-center">
            <TrendingUp size={18} className="text-cat-yeni" />
          </div>
          <div>
            <div className="label-sm">Tamamlanan</div>
            <div className="text-xl font-bold text-text-primary">{completed}</div>
          </div>
        </div>
        <div className="card p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded bg-cat-veje/15 border border-cat-veje/30
                          flex items-center justify-center">
            <Clock size={18} className="text-cat-veje" />
          </div>
          <div>
            <div className="label-sm">Devam Eden</div>
            <div className="text-xl font-bold text-text-primary">{running}</div>
          </div>
        </div>
      </div>

      {/* Job list */}
      {isLoading ? (
        <div className="text-center py-20 text-text-subtle">Yükleniyor…</div>
      ) : !jobs?.length ? (
        <div className="card p-16 text-center">
          <div className="text-text-muted text-lg mb-2">Henüz analiz yok</div>
          <p className="text-text-subtle text-sm mb-6">
            İlk analizi başlatmak için yukarıdaki düğmeye tıklayın
          </p>
          <button onClick={() => navigate("/analysis/new")} className="btn-primary mx-auto">
            <Plus size={14} /> İlk Analizi Başlat
          </button>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-border-subtle bg-bg-elev/40">
                <th className="px-5 py-3 text-left label-sm">ID</th>
                <th className="px-5 py-3 text-left label-sm">Durum</th>
                <th className="px-5 py-3 text-left label-sm">İlerleme</th>
                <th className="px-5 py-3 text-left label-sm">Sonuç</th>
                <th className="px-5 py-3 text-left label-sm">Mod</th>
                <th className="px-5 py-3 text-left label-sm">Oluşturulma</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => {
                const m = job.metric_summary || undefined;
                const objCount = m?.objectCount;
                const changeArea = m?.totalChangedAreaM2;
                const isCompleted = job.status === "completed";
                return (
                  <tr
                    key={job.id}
                    className="border-b border-border-subtle hover:bg-bg-elev/50 cursor-pointer transition-colors"
                    onClick={() => navigate(`/map/${job.id}`)}
                    title={isCompleted ? "Sonucu görüntülemek için tıkla" : "Analizi aç"}
                  >
                    <td className="px-5 py-3 font-mono text-xs text-text-muted">
                      {job.id.slice(0, 12)}…
                    </td>
                    <td className="px-5 py-3">
                      <span className={clsx("badge border", STATUS_COLORS[job.status])}>
                        {STATUS_LABEL[job.status] || job.status}
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-28 bg-bg-base rounded-full h-1 overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${job.progress}%`,
                              background: "linear-gradient(90deg, #0099bb, #00d4ff)",
                            }}
                          />
                        </div>
                        <span className="text-[10px] text-text-muted font-mono w-8">
                          {Math.round(job.progress)}%
                        </span>
                      </div>
                    </td>
                    <td className="px-5 py-3 text-xs text-text-muted">
                      {isCompleted && objCount !== undefined ? (
                        <span className="font-mono">
                          {objCount} nesne
                          {changeArea ? ` • ${Math.round(changeArea)} m²` : ""}
                        </span>
                      ) : (
                        <span className="text-text-subtle">—</span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-xs font-mono text-text-muted">
                      {job.detection_mode || "—"}
                    </td>
                    <td className="px-5 py-3 text-text-muted text-xs">
                      {format(new Date(job.created_at), "d MMM yyyy HH:mm", { locale: tr })}
                    </td>
                    <td className="px-5 py-3 text-right">
                      {isCompleted ? (
                        <span className="inline-flex items-center gap-1 text-[10px] text-accent">
                          <Eye size={12} /> Sonucu Gör
                        </span>
                      ) : (
                        <ChevronRight size={14} className="text-text-subtle ml-auto" />
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
