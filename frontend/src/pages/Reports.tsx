import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import { reportsApi } from "@/api/reports";
import { FileText, Download } from "lucide-react";
import { format } from "date-fns";
import { tr } from "date-fns/locale";
import toast from "react-hot-toast";

interface ReportRow {
  id: string;
  format: string;
  status: string;
  size_bytes: number;
  created_at: string;
  job_id: string;
}

export default function Reports() {
  const { data: reports, isLoading } = useQuery<ReportRow[]>({
    queryKey: ["reports"],
    queryFn: async () => {
      const { data } = await apiClient.get("/reports");
      return data;
    },
  });

  async function handleDownload(id: string) {
    try {
      const url = await reportsApi.getDownloadUrl(id);
      window.open(url, "_blank");
    } catch {
      toast.error("İndirme başlatılamadı");
    }
  }

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-text-primary">Raporlar</h1>
        <p className="text-text-muted text-sm mt-1">
          Üretilmiş PDF ve CSV raporları
        </p>
      </div>

      {isLoading ? (
        <div className="text-center py-20 text-text-subtle">Yükleniyor…</div>
      ) : !reports?.length ? (
        <div className="card p-16 text-center">
          <FileText size={32} className="text-text-subtle mx-auto mb-3" />
          <div className="text-text-muted">Henüz rapor yok</div>
          <p className="text-text-subtle text-sm mt-1">
            Bir analiz tamamlandığında harita ekranından rapor üretebilirsiniz
          </p>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-border-subtle bg-bg-elev/40">
                <th className="px-5 py-3 text-left label-sm">Format</th>
                <th className="px-5 py-3 text-left label-sm">Analiz</th>
                <th className="px-5 py-3 text-left label-sm">Boyut</th>
                <th className="px-5 py-3 text-left label-sm">Tarih</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody>
              {reports.map((r) => (
                <tr key={r.id} className="border-b border-border-subtle hover:bg-bg-elev/50">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2">
                      <FileText size={14} className="text-text-muted" />
                      <span className="font-medium uppercase text-xs text-text-primary">{r.format}</span>
                    </div>
                  </td>
                  <td className="px-5 py-3 font-mono text-xs text-text-muted">
                    {r.job_id.slice(0, 12)}…
                  </td>
                  <td className="px-5 py-3 text-text-muted text-xs">
                    {r.size_bytes ? `${(r.size_bytes / 1024).toFixed(0)} KB` : "—"}
                  </td>
                  <td className="px-5 py-3 text-text-muted text-xs">
                    {format(new Date(r.created_at), "d MMM yyyy HH:mm", { locale: tr })}
                  </td>
                  <td className="px-5 py-3 text-right">
                    <button
                      onClick={() => handleDownload(r.id)}
                      className="btn-ghost text-xs"
                    >
                      <Download size={12} /> İndir
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
