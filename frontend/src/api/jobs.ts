import { apiClient } from "./client";
import type { AnalysisJob, FeatureCollection, ProgressEvent } from "@/types";

export const jobsApi = {
  create: async (params: {
    before_image_id: string;
    after_image_id: string;
    model_id?: string;
    confidence_threshold?: number;
  }): Promise<AnalysisJob> => {
    const { data } = await apiClient.post<AnalysisJob>("/jobs", params);
    return data;
  },

  getResults: async (jobId: string): Promise<FeatureCollection> => {
    const { data } = await apiClient.get<FeatureCollection>(`/jobs/${jobId}/results`);
    return data;
  },

  cancel: async (jobId: string): Promise<void> => {
    await apiClient.delete(`/jobs/${jobId}`);
  },

  streamProgress: (
    jobId: string,
    onProgress: (evt: ProgressEvent) => void,
    onDone: () => void,
    onError: (err: Event) => void
  ): EventSource => {
    const token = localStorage.getItem("access_token");
    const baseUrl = import.meta.env.VITE_API_URL || "/api";
    const es = new EventSource(`${baseUrl}/jobs/${jobId}/progress?token=${token}`);
    es.onmessage = (e) => {
      const parsed: ProgressEvent = JSON.parse(e.data);
      onProgress(parsed);
      if (parsed.progress >= 100 || parsed.message.startsWith("FAILED")) {
        es.close();
        onDone();
      }
    };
    es.onerror = (e) => {
      es.close();
      onError(e);
    };
    return es;
  },
};
