"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import type { Video } from "@/lib/types";
import Link from "next/link";

function badge(status: Video["status"]) {
  const base = "inline-flex items-center rounded-md border px-2 py-0.5 text-xs";
  switch (status) {
    case "READY": return `${base} bg-emerald-50`;
    case "ERROR": return `${base} bg-red-50`;
    default: return base;
  }
}

import { Progress } from "@/components/ui/progress";

// ...

export default function VideosPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["videos"],
    queryFn: () => apiFetch<Video[]>(endpoints.videos),
    refetchInterval: 3000, // Poll every 3 seconds for progress
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Videos</h1>
        <p className="text-sm text-muted-foreground">
          New uploads detected from your monitored channels.
        </p>
      </div>

      {isLoading && <div className="text-sm text-muted-foreground">Loading…</div>}
      {error && <div className="text-sm text-red-500">{String(error)}</div>}

      <div className="rounded-lg border">
        <div className="grid grid-cols-6 gap-2 border-b p-3 text-xs font-medium text-muted-foreground">
          <div className="col-span-2">Title</div>
          <div>Published</div>
          <div className="col-span-2">Status</div>
          <div>Action</div>
        </div>

        {(data || []).map((v) => {
          const showProgress = v.status !== "READY" && v.status !== "ERROR";
          return (
            <div key={v.id} className="grid grid-cols-6 gap-2 p-3 text-sm items-center hover:bg-muted/50 transition-colors">
              <div className="col-span-2 font-medium truncate" title={v.title}>{v.title}</div>
              <div className="text-xs text-muted-foreground">{new Date(v.published_at).toLocaleString()}</div>

              <div className="col-span-2 flex flex-col gap-1.5 pr-4">
                <div className="flex items-center gap-2">
                  <span className={badge(v.status)}>{v.status}</span>
                  {showProgress && (
                    <span className="text-xs text-muted-foreground font-mono">
                      {v.progress}%
                    </span>
                  )}
                </div>
                {showProgress && (
                  <Progress value={v.progress || 0} className="h-1.5" />
                )}
                {v.status === "ERROR" && v.error_message && (
                  <div className="text-xs text-red-500 truncate" title={v.error_message}>
                    {v.error_message}
                  </div>
                )}
              </div>

              <div>
                <Link className="text-sm underline decoration-primary/50 hover:decoration-primary" href={`/videos/${v.id}`}>
                  Open
                </Link>
              </div>
            </div>
          );
        })}

        {!isLoading && (data?.length ?? 0) === 0 && (
          <div className="p-4 text-sm text-muted-foreground">
            No videos yet.
          </div>
        )}
      </div>
    </div>
  );
}

