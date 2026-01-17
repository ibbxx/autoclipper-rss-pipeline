"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import { REFETCH_INTERVALS } from "@/lib/constants";
import { RETRY_CONFIG } from "@/lib/query-config";
import type { PostJob } from "@/lib/types";

export function usePosts(options?: { status?: string }) {
    const url = options?.status
        ? `${endpoints.posts}?status=${options.status}`
        : endpoints.posts;

    return useQuery({
        queryKey: ["posts", options?.status],
        queryFn: () => apiFetch<PostJob[]>(url),
        refetchInterval: REFETCH_INTERVALS.POSTS,
        ...RETRY_CONFIG,
    });
}

