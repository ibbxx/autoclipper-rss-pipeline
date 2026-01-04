"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import type { PostJob } from "@/lib/types";

function badge(status: PostJob["status"]) {
  const base = "inline-flex items-center rounded-md border px-2 py-0.5 text-xs";
  switch (status) {
    case "POSTED": return `${base} bg-emerald-50`;
    case "FAILED": return `${base} bg-red-50`;
    default: return base;
  }
}

export default function PostsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["posts"],
    queryFn: () => apiFetch<PostJob[]>(endpoints.posts),
    refetchInterval: 15000,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Posts (Upload Log)</h1>
        <p className="text-sm text-muted-foreground">
          Track TikTok uploads (queued → uploading → posted).
        </p>
      </div>

      {isLoading && <div className="text-sm text-muted-foreground">Loading…</div>}
      {error && <div className="text-sm text-red-500">{String(error)}</div>}

      <div className="rounded-lg border">
        <div className="grid grid-cols-5 gap-2 border-b p-3 text-xs font-medium text-muted-foreground">
          <div>Clip ID</div>
          <div>Status</div>
          <div>Mode</div>
          <div>Created</div>
          <div>Error</div>
        </div>

        {(data || []).map((p) => (
          <div key={p.id} className="grid grid-cols-5 gap-2 p-3 text-sm">
            <div className="font-mono text-xs">{p.clip_id}</div>
            <div><span className={badge(p.status)}>{p.status}</span></div>
            <div className="text-xs">{p.mode}</div>
            <div className="text-xs">{new Date(p.created_at).toLocaleString()}</div>
            <div className="text-xs text-red-500 truncate">{p.error_message || ""}</div>
          </div>
        ))}

        {!isLoading && (data?.length ?? 0) === 0 && (
          <div className="p-4 text-sm text-muted-foreground">
            No upload jobs yet.
          </div>
        )}
      </div>
    </div>
  );
}
