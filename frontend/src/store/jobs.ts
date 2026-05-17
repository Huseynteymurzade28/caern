import { create } from "zustand";
import type { AnalysisJob, FeatureCollection } from "@/types";

interface JobsState {
  activeJobId: string | null;
  progress: number;
  progressMsg: string;
  results: FeatureCollection | null;
  setActiveJob: (id: string | null) => void;
  setProgress: (pct: number, msg?: string) => void;
  setResults: (fc: FeatureCollection) => void;
  reset: () => void;
}

export const useJobsStore = create<JobsState>((set) => ({
  activeJobId: null,
  progress: 0,
  progressMsg: "",
  results: null,

  setActiveJob: (id) => set({ activeJobId: id, progress: 0, progressMsg: "", results: null }),
  setProgress: (pct, msg = "") => set({ progress: pct, progressMsg: msg }),
  setResults: (fc) => set({ results: fc }),
  reset: () => set({ activeJobId: null, progress: 0, progressMsg: "", results: null }),
}));
