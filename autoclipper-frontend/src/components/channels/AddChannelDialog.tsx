"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import type { Channel } from "@/lib/types";

interface AddChannelDialogProps {
    open: boolean;
    onClose: () => void;
}

interface ResolveResponse {
    channel_id: string | null;
    name: string | null;
    error: string | null;
}

/**
 * Check if input is already a valid Channel ID
 */
function isValidChannelId(input: string): boolean {
    return /^UC[\w-]{22}$/.test(input.trim());
}

/**
 * Extract Channel ID from direct channel URL, or return null if needs resolution
 */
function extractDirectChannelId(input: string): string | null {
    const trimmed = input.trim();

    // Already a channel ID
    if (isValidChannelId(trimmed)) {
        return trimmed;
    }

    // Direct channel URL: youtube.com/channel/UCxxxx
    const match = trimmed.match(/youtube\.com\/channel\/(UC[\w-]{22})/);
    if (match) {
        return match[1];
    }

    return null;
}

export function AddChannelDialog({ open, onClose }: AddChannelDialogProps) {
    const queryClient = useQueryClient();
    const [urlInput, setUrlInput] = useState("");
    const [formData, setFormData] = useState({
        name: "",
        youtube_channel_id: "",
        is_active: true,
        process_latest: false,
        clips_per_video: 4,
        min_clip_sec: 30,
        max_clip_sec: 75,
    });
    const [resolveError, setResolveError] = useState<string | null>(null);

    const resolveMutation = useMutation({
        mutationFn: (url: string) =>
            apiFetch<ResolveResponse>(endpoints.resolveChannel, {
                method: "POST",
                json: { url },
            }),
        onSuccess: (data) => {
            if (data.channel_id) {
                setFormData((prev) => ({
                    ...prev,
                    youtube_channel_id: data.channel_id!,
                    name: prev.name || data.name || "",
                }));
                setResolveError(null);
            } else {
                setResolveError(data.error || "Could not resolve channel ID");
            }
        },
        onError: (error) => {
            setResolveError(String(error));
        },
    });

    const createMutation = useMutation({
        mutationFn: (data: typeof formData) =>
            apiFetch<Channel>(endpoints.channels, {
                method: "POST",
                json: { ...data, is_active: true },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["channels"] });
            resetForm();
            onClose();
        },
    });

    const resetForm = () => {
        setUrlInput("");
        setFormData({
            name: "",
            youtube_channel_id: "",
            is_active: true,
            process_latest: false,
            clips_per_video: 4,
            min_clip_sec: 30,
            max_clip_sec: 75,
        });
        setResolveError(null);
    };

    const handleUrlChange = (value: string) => {
        setUrlInput(value);
        setResolveError(null);

        // Try to extract directly first
        const directId = extractDirectChannelId(value);
        if (directId) {
            setFormData((prev) => ({ ...prev, youtube_channel_id: directId }));
        } else {
            // Clear channel ID - user needs to resolve
            setFormData((prev) => ({ ...prev, youtube_channel_id: "" }));
        }
    };

    const handleResolve = () => {
        if (urlInput.trim()) {
            resolveMutation.mutate(urlInput.trim());
        }
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!isValidChannelId(formData.youtube_channel_id)) {
            setResolveError("Channel ID harus dimulai dengan 'UC' dan 24 karakter. Klik 'Resolve' terlebih dahulu.");
            return;
        }
        createMutation.mutate(formData);
    };

    const handleClose = () => {
        resetForm();
        onClose();
    };

    if (!open) return null;

    const hasValidChannelId = isValidChannelId(formData.youtube_channel_id);
    const needsResolve = urlInput.trim() && !hasValidChannelId && !extractDirectChannelId(urlInput);

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            {/* Backdrop */}
            <div className="absolute inset-0 bg-black/50" onClick={handleClose} />

            {/* Dialog */}
            <div className="relative z-10 w-full max-w-md rounded-xl border bg-background p-6 shadow-lg">
                <h2 className="text-lg font-semibold">Add YouTube Channel</h2>
                <p className="text-sm text-muted-foreground mb-4">
                    Paste a YouTube channel URL, video URL, or @handle to start auto-clipping.
                </p>

                <form onSubmit={handleSubmit} className="space-y-4">
                    {/* Channel Name */}
                    <div>
                        <label className="block text-sm font-medium mb-1">
                            Channel Name
                        </label>
                        <input
                            type="text"
                            required
                            placeholder="e.g. MrBeast"
                            className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                            value={formData.name}
                            onChange={(e) =>
                                setFormData((prev) => ({ ...prev, name: e.target.value }))
                            }
                        />
                    </div>

                    {/* YouTube URL/ID Input */}
                    <div>
                        <label className="block text-sm font-medium mb-1">
                            YouTube URL or Handle
                        </label>
                        <div className="flex gap-2">
                            <input
                                type="text"
                                required
                                placeholder="https://youtube.com/@handle atau video URL"
                                className="flex-1 rounded-md border bg-background px-3 py-2 text-sm"
                                value={urlInput}
                                onChange={(e) => handleUrlChange(e.target.value)}
                            />
                            {needsResolve && (
                                <button
                                    type="button"
                                    onClick={handleResolve}
                                    disabled={resolveMutation.isPending}
                                    className="rounded-md bg-blue-600 px-3 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
                                >
                                    {resolveMutation.isPending ? "..." : "Resolve"}
                                </button>
                            )}
                        </div>

                        {/* Extracted Channel ID */}
                        {formData.youtube_channel_id && (
                            <div className="mt-2 p-2 rounded-md bg-muted">
                                <div className="text-xs text-muted-foreground">Detected Channel ID:</div>
                                <div className={`font-mono text-sm ${hasValidChannelId ? 'text-emerald-600' : 'text-amber-600'}`}>
                                    {formData.youtube_channel_id}
                                    {hasValidChannelId ? ' ✓' : ' (Format tidak valid)'}
                                </div>
                            </div>
                        )}

                        {/* Resolve hint */}
                        {needsResolve && !formData.youtube_channel_id && !resolveMutation.isPending && (
                            <p className="text-xs text-blue-600 mt-1">
                                Klik &quot;Resolve&quot; untuk mendapatkan Channel ID dari URL ini
                            </p>
                        )}

                        {/* Error message */}
                        {resolveError && (
                            <p className="text-xs text-red-500 mt-1">{resolveError}</p>
                        )}

                        <p className="text-xs text-muted-foreground mt-1">
                            Contoh: youtube.com/@ytberfavkamu, youtube.com/watch?v=xxx
                        </p>
                    </div>

                    {/* Monitoring Options */}
                    <div className="space-y-2 py-2 border-t border-b">
                        <div className="flex items-center gap-2">
                            <input
                                type="checkbox"
                                id="is_active"
                                checked={formData.is_active}
                                onChange={(e) =>
                                    setFormData((prev) => ({ ...prev, is_active: e.target.checked }))
                                }
                                className="h-4 w-4"
                            />
                            <label htmlFor="is_active" className="text-sm">
                                Aktifkan Monitoring (otomatis proses video baru)
                            </label>
                        </div>

                        <div className="flex items-center gap-2">
                            <input
                                type="checkbox"
                                id="process_latest"
                                checked={formData.process_latest}
                                onChange={(e) =>
                                    setFormData((prev) => ({ ...prev, process_latest: e.target.checked }))
                                }
                                className="h-4 w-4"
                            />
                            <label htmlFor="process_latest" className="text-sm">
                                Proses 1 video terbaru sekarang
                            </label>
                        </div>
                    </div>

                    {/* Clips per Video */}
                    <div>
                        <label className="block text-sm font-medium mb-1">
                            Clips per Video
                        </label>
                        <input
                            type="number"
                            min={1}
                            max={10}
                            className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                            value={formData.clips_per_video}
                            onChange={(e) =>
                                setFormData((prev) => ({
                                    ...prev,
                                    clips_per_video: parseInt(e.target.value) || 4,
                                }))
                            }
                        />
                    </div>

                    {/* Clip Duration */}
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium mb-1">
                                Min Duration (sec)
                            </label>
                            <input
                                type="number"
                                min={5}
                                max={120}
                                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                                value={formData.min_clip_sec}
                                onChange={(e) =>
                                    setFormData((prev) => ({
                                        ...prev,
                                        min_clip_sec: parseInt(e.target.value) || 20,
                                    }))
                                }
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium mb-1">
                                Max Duration (sec)
                            </label>
                            <input
                                type="number"
                                min={6}
                                max={180}
                                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                                value={formData.max_clip_sec}
                                onChange={(e) =>
                                    setFormData((prev) => ({
                                        ...prev,
                                        max_clip_sec: parseInt(e.target.value) || 45,
                                    }))
                                }
                            />
                        </div>
                    </div>

                    {/* Error Message */}
                    {createMutation.error && (
                        <div className="text-sm text-red-500">
                            {String(createMutation.error)}
                        </div>
                    )}

                    {/* Actions */}
                    <div className="flex justify-end gap-2 pt-2">
                        <button
                            type="button"
                            onClick={handleClose}
                            className="rounded-md border px-4 py-2 text-sm hover:bg-muted"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={createMutation.isPending || !hasValidChannelId}
                            className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                        >
                            {createMutation.isPending ? "Adding..." : "Add Channel"}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
