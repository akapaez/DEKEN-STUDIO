"use client";

import type { JobStatus, Schemas } from "@deken/shared";
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { api, unwrap } from "./api";

export type Me = Schemas["MeOut"];
export type SystemStatus = Schemas["SystemStatusOut"];
export type Job = Schemas["JobOut"];
export type JobDetail = Schemas["JobDetailOut"];
export type User = Schemas["UserOut"];
export type WorkerInfo = Schemas["WorkerOut"];
export type AuditEvent = Schemas["AuditEventOut"];
export type MediaAsset = Schemas["MediaAssetOut"];
export type MediaAssetDetail = Schemas["MediaAssetDetailOut"];
export type BrandAsset = Schemas["BrandAssetOut"];
export type RenderEngine = Schemas["RenderEngineOut"];

export interface MediaFilters {
  q?: string;
  tag?: string[];
  status?: string;
  orientation?: "vertical" | "horizontal" | "square";
  has_audio?: boolean;
  consent?: "not_required" | "pending" | "granted" | "denied";
}

/** Estados de un activo que aún pueden cambiar sin intervención (sondeo). */
export const MEDIA_IN_PROGRESS: ReadonlySet<string> = new Set(["uploading", "processing"]);

const TERMINAL: ReadonlySet<JobStatus> = new Set(["completed", "failed", "cancelled"]);
export const isTerminal = (status: JobStatus): boolean => TERMINAL.has(status);

export const keys = {
  me: ["me"] as const,
  status: ["system-status"] as const,
  jobs: (status?: JobStatus) => ["jobs", status ?? "all"] as const,
  job: (id: string) => ["job", id] as const,
  users: ["users"] as const,
  roles: ["roles"] as const,
  workers: ["workers"] as const,
  audit: (outcome?: string) => ["audit", outcome ?? "all"] as const,
  media: ["media"] as const,
  mediaList: (filters: MediaFilters) => ["media", "list", filters] as const,
  mediaAsset: (id: string) => ["media", "asset", id] as const,
  mediaTags: ["media", "tags"] as const,
  waveform: (id: string) => ["media", "waveform", id] as const,
  brand: ["brand"] as const,
  renderEngine: ["render-engine"] as const,
};

export function useMe() {
  return useQuery({
    queryKey: keys.me,
    queryFn: () => unwrap(api.GET("/api/v1/auth/me")),
    staleTime: 60_000,
  });
}

export function useSystemStatus() {
  return useQuery({
    queryKey: keys.status,
    queryFn: () => unwrap(api.GET("/api/v1/system/status")),
    refetchInterval: 10_000,
  });
}

export function useJobs(status?: JobStatus, limit = 50) {
  return useQuery({
    queryKey: [...keys.jobs(status), limit],
    queryFn: () => unwrap(api.GET("/api/v1/jobs", { params: { query: { status, limit } } })),
    refetchInterval: 3_000,
  });
}

export function useJob(id: string | null) {
  return useQuery({
    queryKey: keys.job(id ?? "none"),
    queryFn: () => unwrap(api.GET("/api/v1/jobs/{job_id}", { params: { path: { job_id: id ?? "" } } })),
    enabled: id !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.job.status;
      return status && isTerminal(status) ? false : 1_000;
    },
  });
}

export function useUsers(enabled = true) {
  return useQuery({ queryKey: keys.users, queryFn: () => unwrap(api.GET("/api/v1/users")), enabled });
}

export function useRoles() {
  return useQuery({ queryKey: keys.roles, queryFn: () => unwrap(api.GET("/api/v1/users/roles")), staleTime: Infinity });
}

export function useWorkers() {
  return useQuery({
    queryKey: keys.workers,
    queryFn: () => unwrap(api.GET("/api/v1/workers")),
    refetchInterval: 10_000,
  });
}

export function useAudit(outcome?: "success" | "failure" | "denied") {
  return useQuery({
    queryKey: keys.audit(outcome),
    queryFn: () => unwrap(api.GET("/api/v1/audit", { params: { query: { outcome, limit: 100 } } })),
  });
}

export function useInvalidate() {
  const client = useQueryClient();
  return (...queryKeys: ReadonlyArray<readonly unknown[]>) =>
    Promise.all(queryKeys.map((queryKey) => client.invalidateQueries({ queryKey })));
}

export function useLogout() {
  const client = useQueryClient();
  const router = useRouter();
  return useMutation({
    mutationFn: () => unwrap(api.POST("/api/v1/auth/logout")),
    onSettled: () => {
      client.clear();
      router.replace("/login");
      router.refresh();
    },
  });
}

const MEDIA_PAGE = 48;

export function useMediaAssets(filters: MediaFilters) {
  return useInfiniteQuery({
    queryKey: keys.mediaList(filters),
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      unwrap(api.GET("/api/v1/media/assets", { params: { query: { ...filters, limit: MEDIA_PAGE, offset: pageParam } } })),
    getNextPageParam: (last, pages) => {
      const loaded = pages.reduce((n, p) => n + p.items.length, 0);
      return loaded < last.total ? loaded : undefined;
    },
    refetchInterval: (query) =>
      query.state.data?.pages.some((p) => p.items.some((a) => MEDIA_IN_PROGRESS.has(a.status))) ? 3_000 : 60_000,
  });
}

export function useMediaAsset(id: string) {
  return useQuery({
    queryKey: keys.mediaAsset(id),
    queryFn: () => unwrap(api.GET("/api/v1/media/assets/{asset_id}", { params: { path: { asset_id: id } } })),
    refetchInterval: (query) => (MEDIA_IN_PROGRESS.has(query.state.data?.status ?? "") ? 2_000 : false),
  });
}

export function useMediaTags() {
  return useQuery({ queryKey: keys.mediaTags, queryFn: () => unwrap(api.GET("/api/v1/media/tags")) });
}

export function useWaveform(id: string, enabled: boolean) {
  return useQuery({
    queryKey: keys.waveform(id),
    queryFn: () => unwrap(api.GET("/api/v1/media/assets/{asset_id}/waveform", { params: { path: { asset_id: id } } })),
    enabled,
    staleTime: Infinity,
  });
}

export function useBrandAssets() {
  return useQuery({ queryKey: keys.brand, queryFn: () => unwrap(api.GET("/api/v1/brand/assets")) });
}

export function useRenderEngine() {
  return useQuery({
    queryKey: keys.renderEngine,
    queryFn: () => unwrap(api.GET("/api/v1/renders/engine")),
    refetchInterval: 15_000,
  });
}
