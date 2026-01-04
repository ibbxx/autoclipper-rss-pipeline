"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import type { Video } from "@/lib/types";
import Link from "next/link";
import { useParams } from "next/navigation";

export default function VideoDetailPage() {
  const params = useParams<{ videoId: string }>();
  const videoId = params.videoId;

  const { data, isLoading, error } = useQuery({
    queryKey: ["video", videoId],
    queryFn: () => apiFetch<Video>(endpoints.video(videoId)),
    refetchInterval: 15000,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Video Detail</h1>
          <p className="text-sm text-muted-foreground">Status & processing timeline.</p>
        </div>
        <div className="flex gap-2">
          <Link className="rounded-md border px-3 py-2 text-sm hover:bg-muted" href={`/clips/${videoId}`}>
            Open Clips Review
          </Link>
          <button className="rounded-md border px-3 py-2 text-sm hover:bg-muted">
            Reprocess (placeholder)
          </button>
        </div>
      </div>

      {isLoading && <div className="text-sm text-muted-foreground">Loading…</div>}
      {error && <div className="text-sm text-red-500">{String(error)}</div>}

      {data && (
        <div className="rounded-lg border p-4 space-y-2">
          <div className="text-sm"><span className="text-muted-foreground">Title:</span> {data.title}</div>
          <div className="text-sm"><span className="text-muted-foreground">Status:</span> {data.status}</div>
          <div className="text-sm"><span className="text-muted-foreground">Published:</span> {new Date(data.published_at).toLocaleString()}</div>
          {data.error_message && (
            <div className="text-sm text-red-500">{data.error_message}</div>
          )}
        </div>
      )}
    </div>
  );
}
