"use client";

import { useState, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import type { Channel } from "@/lib/types";

interface EditChannelDialogProps {
    channel: Channel | null;
    open: boolean;
    onClose: () => void;
}

export function EditChannelDialog({ channel, open, onClose }: EditChannelDialogProps) {
    const queryClient = useQueryClient();
    const [formData, setFormData] = useState({
        name: "",
        clips_per_video: 4,
        min_clip_sec: 20,
        max_clip_sec: 45,
        is_active: true,
    });

    // Sync form data when channel changes
    useEffect(() => {
        if (channel) {
            setFormData({
                name: channel.name,
                clips_per_video: channel.clips_per_video,
                min_clip_sec: channel.min_clip_sec,
                max_clip_sec: channel.max_clip_sec,
                is_active: channel.is_active,
            });
        }
    }, [channel]);

    const updateMutation = useMutation({
        mutationFn: (data: typeof formData) =>
            apiFetch<Channel>(endpoints.channel(channel!.id), {
                method: "PATCH",
                json: data,
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["channels"] });
            onClose();
        },
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        updateMutation.mutate(formData);
    };

    if (!open || !channel) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            {/* Backdrop */}
            <div className="absolute inset-0 bg-black/50" onClick={onClose} />

            {/* Dialog */}
            <div className="relative z-10 w-full max-w-md rounded-xl border bg-background p-6 shadow-lg">
                <h2 className="text-lg font-semibold">Edit Channel</h2>
                <p className="text-sm text-muted-foreground mb-4">
                    Update pengaturan untuk channel {channel.name}
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
                            className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                            value={formData.name}
                            onChange={(e) =>
                                setFormData((prev) => ({ ...prev, name: e.target.value }))
                            }
                        />
                    </div>

                    {/* Channel ID (read-only) */}
                    <div>
                        <label className="block text-sm font-medium mb-1">
                            YouTube Channel ID
                        </label>
                        <div className="w-full rounded-md border bg-muted px-3 py-2 text-sm font-mono text-muted-foreground">
                            {channel.youtube_channel_id}
                        </div>
                    </div>

                    {/* Active Status */}
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
                            Channel Aktif (akan diproses otomatis)
                        </label>
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
                    {updateMutation.error && (
                        <div className="text-sm text-red-500">
                            {String(updateMutation.error)}
                        </div>
                    )}

                    {/* Actions */}
                    <div className="flex justify-end gap-2 pt-2">
                        <button
                            type="button"
                            onClick={onClose}
                            className="rounded-md border px-4 py-2 text-sm hover:bg-muted"
                        >
                            Batal
                        </button>
                        <button
                            type="submit"
                            disabled={updateMutation.isPending}
                            className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                        >
                            {updateMutation.isPending ? "Menyimpan..." : "Simpan"}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
