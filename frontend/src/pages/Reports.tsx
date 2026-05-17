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
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Raporlar</h1>

      {isLoading ? (
        <div className="text-center py-20 text-gray-400">Yükleniyor...</div>
      ) : !reports?.length ? (
        <div className="text-center py-20 text-gray-400">Henüz rapor yok.</div>
      ) : (
        <div className="bg-white rounded-xl shadow overflow-hidden">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Format</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Job</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Boyut</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Tarih</th>
                <th className="px-6 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {reports.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <FileText size={16} className="text-gray-400" />
                      <span className="font-medium uppercase text-xs">{r.format}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 font-mono text-xs text-gray-500">{r.job_id.slice(0, 8)}…</td>
                  <td className="px-6 py-4 text-gray-500 text-xs">
                    {r.size_bytes ? `${(r.size_bytes / 1024).toFixed(0)} KB` : "—"}
                  </td>
                  <td className="px-6 py-4 text-gray-500 text-xs">
                    {format(new Date(r.created_at), "d MMM yyyy HH:mm", { locale: tr })}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => handleDownload(r.id)}
                      className="flex items-center gap-1 text-primary-600 hover:text-primary-700 text-xs font-medium ml-auto"
                    >
                      <Download size={14} />
                      İndir
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
