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

export default function VideosPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["videos"],
    queryFn: () => apiFetch<Video[]>(endpoints.videos),
    refetchInterval: 30000,
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
          <div className="col-span-3">Title</div>
          <div>Published</div>
          <div>Status</div>
          <div>Action</div>
        </div>

        {(data || []).map((v) => (
          <div key={v.id} className="grid grid-cols-6 gap-2 p-3 text-sm">
            <div className="col-span-3 font-medium">{v.title}</div>
            <div className="text-xs">{new Date(v.published_at).toLocaleString()}</div>
            <div><span className={badge(v.status)}>{v.status}</span></div>
            <div>
              <Link className="text-sm underline" href={`/videos/${v.id}`}>
                Open
              </Link>
            </div>
          </div>
        ))}

        {!isLoading && (data?.length ?? 0) === 0 && (
          <div className="p-4 text-sm text-muted-foreground">
            No videos yet.
          </div>
        )}
      </div>
    </div>
  );
}
