"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import { REFETCH_INTERVALS } from "@/lib/constants";
import { RETRY_CONFIG } from "@/lib/query-config";
import type { Video } from "@/lib/types";

export function useVideos(options?: { status?: string; channelId?: string }) {
    const queryParams = new URLSearchParams();
    if (options?.status) queryParams.set("status", options.status);
    if (options?.channelId) queryParams.set("channel_id", options.channelId);

    const url = queryParams.toString()
        ? `${endpoints.videos}?${queryParams}`
        : endpoints.videos;

    return useQuery({
        queryKey: ["videos", options?.status, options?.channelId],
        queryFn: () => apiFetch<Video[]>(url),
        refetchInterval: REFETCH_INTERVALS.VIDEOS,
        ...RETRY_CONFIG,
    });
}

export function useVideo(videoId: string) {
    return useQuery({
        queryKey: ["video", videoId],
        queryFn: () => apiFetch<Video>(endpoints.video(videoId)),
        refetchInterval: REFETCH_INTERVALS.VIDEO_DETAIL,
        ...RETRY_CONFIG,
    });
}

