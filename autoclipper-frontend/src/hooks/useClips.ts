"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import { REFETCH_INTERVALS } from "@/lib/constants";
import { RETRY_CONFIG } from "@/lib/query-config";
import type { Clip } from "@/lib/types";

export function useClips(videoId: string) {
    return useQuery({
        queryKey: ["clips", videoId],
        queryFn: () => apiFetch<Clip[]>(endpoints.clipsByVideo(videoId)),
        refetchInterval: REFETCH_INTERVALS.CLIPS,
        ...RETRY_CONFIG,
    });
}

export function useApproveClips(videoId: string) {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (params: { clipIds: string[]; mode: "DRAFT" | "DIRECT" }) => {
            return apiFetch<{ ok: boolean }>(endpoints.approveVideoClips(videoId), {
                method: "POST",
                json: { clip_ids: params.clipIds, mode: params.mode },
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["clips", videoId] });
        },
    });
}

export function useClipSelection(clips: Clip[] | undefined) {
    const [selected, setSelected] = useState<Record<string, boolean>>({});

    useEffect(() => {
        if (!clips) return;
        const next: Record<string, boolean> = {};
        for (const c of clips) {
            next[c.id] = c.render_status === "READY";
        }
        setSelected(next);
    }, [clips]);

    const toggleClip = (clipId: string, checked: boolean) => {
        setSelected((prev) => ({ ...prev, [clipId]: checked }));
    };

    const selectedIds = Object.entries(selected)
        .filter(([, v]) => v)
        .map(([id]) => id);

    const selectedCount = selectedIds.length;

    return { selected, toggleClip, selectedIds, selectedCount };
}

// Need to import these for the hook
import { useState, useEffect } from "react";
