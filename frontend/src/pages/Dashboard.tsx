import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { apiClient } from "@/api/client";
import type { AnalysisJob } from "@/types";
import { format } from "date-fns";
import { tr } from "date-fns/locale";
import { Plus, ChevronRight } from "lucide-react";
import clsx from "clsx";

const STATUS_COLORS: Record<string, string> = {
  completed: "bg-green-100 text-green-800",
  running: "bg-blue-100 text-blue-800",
  failed: "bg-red-100 text-red-800",
  queued: "bg-yellow-100 text-yellow-800",
  cancelled: "bg-gray-100 text-gray-600",
};

export default function Dashboard() {
  const navigate = useNavigate();
  const { data: jobs, isLoading } = useQuery<AnalysisJob[]>({
    queryKey: ["jobs"],
    queryFn: async () => {
      const { data } = await apiClient.get("/jobs");
      return data;
    },
  });

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 text-sm mt-1">Son analiz işleri</p>
        </div>
        <button
          onClick={() => navigate("/analysis/new")}
          className="flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          <Plus size={16} />
          Yeni Analiz
        </button>
      </div>

      {isLoading ? (
        <div className="text-center py-20 text-gray-400">Yükleniyor...</div>
      ) : !jobs?.length ? (
        <div className="text-center py-20 text-gray-400">
          <p className="text-lg">Henüz analiz yok.</p>
          <p className="text-sm mt-2">İlk analizi başlatmak için "Yeni Analiz" düğmesine tıklayın.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow overflow-hidden">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">ID</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Durum</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">İlerleme</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Tarih</th>
                <th className="px-6 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {jobs.map((job) => (
                <tr key={job.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => navigate(`/map/${job.id}`)}>
                  <td className="px-6 py-4 font-mono text-xs text-gray-500">{job.id.slice(0, 8)}…</td>
                  <td className="px-6 py-4">
                    <span className={clsx("px-2 py-1 rounded-full text-xs font-medium", STATUS_COLORS[job.status] || "bg-gray-100")}>
                      {job.status}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="w-32 bg-gray-200 rounded-full h-1.5">
                      <div
                        className="bg-primary-600 h-1.5 rounded-full"
                        style={{ width: `${job.progress}%` }}
                      />
                    </div>
                  </td>
                  <td className="px-6 py-4 text-gray-500 text-xs">
                    {format(new Date(job.created_at), "d MMM yyyy HH:mm", { locale: tr })}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <ChevronRight size={16} className="text-gray-400 ml-auto" />
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
