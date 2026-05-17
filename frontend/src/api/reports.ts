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
};
