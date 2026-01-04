"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import type { Channel } from "@/lib/types";

interface BackfillDialogProps {
    channel: Channel | null;
    open: boolean;
    onClose: () => void;
}

export function BackfillDialog({ channel, open, onClose }: BackfillDialogProps) {
    const queryClient = useQueryClient();
    const [count, setCount] = useState(3);
    const [result, setResult] = useState<{ processed: number; skipped: number } | null>(null);

    const backfillMutation = useMutation({
        mutationFn: (data: { channelId: string; count: number }) =>
            apiFetch<{ ok: boolean; processed: number; skipped: number }>(
                endpoints.backfillChannel(data.channelId, data.count),
                { method: "POST" }
            ),
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ["channels"] });
            setResult({ processed: data.processed, skipped: data.skipped });
        },
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (channel) {
            backfillMutation.mutate({ channelId: channel.id, count });
        }
    };

    const handleClose = () => {
        setCount(3);
        setResult(null);
        onClose();
    };

    if (!open || !channel) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div className="absolute inset-0 bg-black/50" onClick={handleClose} />

            <div className="relative z-10 w-full max-w-sm rounded-xl border bg-background p-6 shadow-lg">
                <h2 className="text-lg font-semibold mb-2">Backfill Videos</h2>
                <p className="text-sm text-muted-foreground mb-4">
                    Proses video lama dari channel <strong>{channel.name}</strong>.<br />
                    Baseline monitoring tidak akan berubah.
                </p>

                {!result ? (
                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium mb-1">
                                Jumlah Video (Max 10)
                            </label>
                            <input
                                type="number"
                                min={1}
                                max={10}
                                required
                                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                                value={count}
                                onChange={(e) => setCount(parseInt(e.target.value) || 3)}
                            />
                        </div>

                        {backfillMutation.error && (
                            <div className="text-sm text-red-500">
                                Error: {String(backfillMutation.error)}
                            </div>
                        )}

                        <div className="flex justify-end gap-2 pt-2">
                            <button
                                type="button"
                                onClick={handleClose}
                                className="rounded-md border px-4 py-2 text-sm hover:bg-muted"
                            >
                                Batal
                            </button>
                            <button
                                type="submit"
                                disabled={backfillMutation.isPending}
                                className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                            >
                                {backfillMutation.isPending ? "Memproses..." : "Mulai Backfill"}
                            </button>
                        </div>
                    </form>
                ) : (
                    <div className="space-y-4">
                        <div className="p-3 bg-green-50 text-green-700 border border-green-200 rounded-md text-sm">
                            <p className="font-semibold">Berhasil!</p>
                            <ul className="list-disc list-inside mt-1">
                                <li>Diproses: {result.processed} video</li>
                                <li>Dilewati (sudah ada): {result.skipped} video</li>
                            </ul>
                        </div>
                        <div className="flex justify-end pt-2">
                            <button
                                onClick={handleClose}
                                className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90"
                            >
                                Tutup
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
