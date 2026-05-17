import { apiClient } from "./client";
import type { GeoImage } from "@/types";

export const imagesApi = {
  upload: async (file: File): Promise<GeoImage> => {
    const form = new FormData();
    form.append("file", file);
    const { data } = await apiClient.post<GeoImage>("/images", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },

  get: async (id: string): Promise<GeoImage> => {
    const { data } = await apiClient.get<GeoImage>(`/images/${id}`);
    return data;
  },
};
