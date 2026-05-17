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

export interface ChangeFeature {
  type: "Feature";
  id: string;
  geometry: GeoJSON.Polygon;
  properties: {
    classLabel: string;
    confidence: number;
    changeType: "new" | "lost";
    areaM2: number | null;
  };
}

export interface FeatureCollection {
  type: "FeatureCollection";
  features: ChangeFeature[];
  metadata: {
    jobId: string;
    status: string;
    featureCount: number;
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
