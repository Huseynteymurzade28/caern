import { apiClient } from "./client";

export const reportsApi = {
  create: async (job_id: string, format: "pdf" | "csv") => {
    const { data } = await apiClient.post("/reports", { job_id, format });
    return data;
  },

  getDownloadUrl: async (reportId: string): Promise<string> => {
    const { data } = await apiClient.get(`/reports/${reportId}/download`);
    return data.download_url;
  },

  /**
   * Doğrudan raporu (PDF veya CSV) backend'den stream eder ve tarayıcıda
   * dosyayı indirir. MinIO yükleme + presigned-URL adımlarını atlar.
   */
  streamDownload: async (jobId: string, format: "pdf" | "csv"): Promise<void> => {
    const response = await apiClient.get(`/reports/jobs/${jobId}/download.${format}`, {
      responseType: "blob",
    });
    const blob = new Blob([response.data], {
      type: format === "pdf" ? "application/pdf" : "text/csv;charset=utf-8",
    });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `caern_analiz_${jobId.slice(0, 8)}.${format}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  },
};
