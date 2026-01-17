"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import { RETRY_CONFIG } from "@/lib/query-config";
import type { Channel } from "@/lib/types";

export function useChannels() {
    return useQuery({
        queryKey: ["channels"],
        queryFn: () => apiFetch<Channel[]>(endpoints.channels),
        ...RETRY_CONFIG,
    });
}

