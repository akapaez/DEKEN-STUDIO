"use client";

import type { JobStatus, Schemas } from "@deken/shared";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { api, unwrap } from "./api";

export type Me = Schemas["MeOut"];
export type SystemStatus = Schemas["SystemStatusOut"];
export type Job = Schemas["JobOut"];
export type JobDetail = Schemas["JobDetailOut"];
export type User = Schemas["UserOut"];
export type WorkerInfo = Schemas["WorkerOut"];
export type AuditEvent = Schemas["AuditEventOut"];

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
