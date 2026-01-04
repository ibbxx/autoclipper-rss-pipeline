"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import type { Video } from "@/lib/types";

interface AddVideoDialogProps {
    open: boolean;
    onClose: () => void;
}

export function AddVideoDialog({ open, onClose }: AddVideoDialogProps) {
    const queryClient = useQueryClient();
    const [videoUrl, setVideoUrl] = useState("");
    const [result, setResult] = useState<{ type: "success" | "exists" | "error"; message: string } | null>(null);

    const createMutation = useMutation({
        mutationFn: (video_url: string) =>
            apiFetch<Video>(endpoints.videos, {
                method: "POST",
                json: { video_url },
            }),
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ["videos"] });
            setResult({
                type: "success",
                message: `Video "${data.title}" sedang diproses.`,
            });
        },
        onError: (error) => {
            setResult({
                type: "error",
                message: String(error),
            });
        },
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setResult(null);
        if (videoUrl.trim()) {
            createMutation.mutate(videoUrl.trim());
        }
    };

    const handleClose = () => {
        setVideoUrl("");
        setResult(null);
        onClose();
    };

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div className="absolute inset-0 bg-black/50" onClick={handleClose} />

            <div className="relative z-10 w-full max-w-md rounded-xl border bg-background p-6 shadow-lg">
                <h2 className="text-lg font-semibold">Tambah Video</h2>
                <p className="text-sm text-muted-foreground mb-4">
                    Proses satu video langsung dari URL. Tidak perlu tambah channel.
                </p>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium mb-1">
                            Link Video YouTube
                        </label>
                        <input
                            type="text"
                            required
                            placeholder="https://youtube.com/watch?v=xxx"
                            className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                            value={videoUrl}
                            onChange={(e) => setVideoUrl(e.target.value)}
                        />
                        <p className="text-xs text-muted-foreground mt-1">
                            Paste link video YouTube yang ingin diproses
                        </p>
                    </div>

                    {result && (
                        <div
                            className={`text-sm p-3 rounded-md ${result.type === "success"
                                    ? "bg-green-50 text-green-700 border border-green-200"
                                    : result.type === "exists"
                                        ? "bg-amber-50 text-amber-700 border border-amber-200"
                                        : "bg-red-50 text-red-700 border border-red-200"
                                }`}
                        >
                            {result.message}
                        </div>
                    )}

                    <div className="flex justify-end gap-2 pt-2">
                        <button
                            type="button"
                            onClick={handleClose}
                            className="rounded-md border px-4 py-2 text-sm hover:bg-muted"
                        >
                            {result?.type === "success" ? "Tutup" : "Batal"}
                        </button>
                        {!result?.type || result.type !== "success" ? (
                            <button
                                type="submit"
                                disabled={createMutation.isPending}
                                className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                            >
                                {createMutation.isPending ? "Memproses..." : "Proses Sekarang"}
                            </button>
                        ) : null}
                    </div>
                </form>
            </div>
        </div>
    );
}
