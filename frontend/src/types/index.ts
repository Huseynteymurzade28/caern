export type UserRole = "admin" | "analist" | "viewer" | "ai_engineer";

export interface User {
  id: string;
  email: string;
  username: string;
  role: UserRole;
  is_active: boolean;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export type JobStatus =
  | "created" | "validating" | "queued" | "running"
  | "aggregating" | "completed" | "failed" | "cancelled" | "archived";

export interface AnalysisJob {
  id: string;
  status: JobStatus;
  progress: number;
  created_at: string;
  owner_id: string;
  confidence_threshold: number;
  min_area_m2?: number;
  detection_mode?: string | null;
}

export interface GeoImage {
  id: string;
  filename: string;
  format: string;
  size_bytes: number;
  width: number | null;
  height: number | null;
  crs: string | null;
}

export type ChangeCategory = "YENI_YAPI" | "YIKIM" | "VEJETASYON" | "YUZEY_DEG";

export interface ChangeFeature {
  type: "Feature";
  id: string;
  geometry: GeoJSON.Polygon;
  properties: {
    category?: ChangeCategory | string;
    classLabel?: string;
    confidence: number;
    changeType?: ChangeCategory | "new" | "lost" | string;
    areaM2: number | null;
    areaPx?: number | null;
    centroid?: [number, number] | null;
    bbox?: [number, number, number, number] | null;
  };
}

export interface CategorySummary {
  count: number;
  areaM2: number;
}

export interface HistogramBin {
  bin: number;
  range_min: number;
  range_max: number;
  count: number;
}

export interface MetricSummary {
  totalAreaM2?: number;
  totalAreaKm2?: number;
  totalChangedAreaM2?: number;
  totalChangedAreaKm2?: number;
  changePercent?: number;
  objectCount?: number;
  avgConfidence?: number;
  byCategory?: Record<ChangeCategory, CategorySummary>;
  topRegions?: { type: "FeatureCollection"; features: ChangeFeature[] };
  pixelDiffHistogram?: HistogramBin[];
  pixelAreaM2?: number;
  detection_mode?: string;
}

export interface FeatureCollection {
  type: "FeatureCollection";
  features: ChangeFeature[];
  metadata: {
    jobId: string;
    status: string;
    featureCount: number;
    detectionMode?: string;
    metrics?: MetricSummary;
  };
}

export interface Report {
  id: string;
  format: "pdf" | "csv";
  status: string;
  storage_path: string | null;
  size_bytes: number | null;
  created_at: string;
}

export interface AIModel {
  id: string;
  name: string;
  version: string;
  model_type: string;
  is_active: boolean;
  f1_score: number | null;
}

export interface ProgressEvent {
  progress: number;
  message: string;
}
