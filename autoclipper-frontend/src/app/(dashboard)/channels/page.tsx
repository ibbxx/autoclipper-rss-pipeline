"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useChannels } from "@/hooks/useChannels";
import { AddChannelDialog } from "@/components/channels/AddChannelDialog";
import { EditChannelDialog } from "@/components/channels/EditChannelDialog";
import { BackfillDialog } from "@/components/channels/BackfillDialog";
import { AddVideoDialog } from "@/components/videos/AddVideoDialog";
import { PageHeader } from "@/components/layout/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { apiFetch } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import type { Channel } from "@/lib/types";

export default function ChannelsPage() {
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useChannels();
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [showAddVideoDialog, setShowAddVideoDialog] = useState(false);
  const [editingChannel, setEditingChannel] = useState<Channel | null>(null);
  const [backfillChannel, setBackfillChannel] = useState<Channel | null>(null);

  const deleteMutation = useMutation({
    mutationFn: (channelId: string) =>
      apiFetch<{ ok: boolean }>(endpoints.channel(channelId), {
        method: "DELETE",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["channels"] });
    },
  });

  const handleDelete = (channel: Channel) => {
    if (confirm(`Yakin ingin menghapus channel "${channel.name}"?`)) {
      deleteMutation.mutate(channel.id);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Channels"
        description="Kelola channel YouTube untuk auto-clipping. Output: TikTok 9:16 (1080×1920)."
        action={
          <div className="flex gap-2">
            <button
              onClick={() => setShowAddVideoDialog(true)}
              className="rounded-md border bg-background px-4 py-2 text-sm hover:bg-muted"
            >
              + Tambah Video
            </button>
            <button
              onClick={() => setShowAddDialog(true)}
              className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90"
            >
              + Tambah Channel
            </button>
          </div>
        }
      />

      {isLoading && <div className="text-sm text-muted-foreground">Loading…</div>}
      {error && <div className="text-sm text-red-500">{String(error)}</div>}

      <div className="rounded-lg border">
        <div className="grid grid-cols-7 gap-2 border-b p-3 text-xs font-medium text-muted-foreground">
          <div>Nama</div>
          <div className="col-span-2">YouTube Channel ID</div>
          <div>Status</div>
          <div>Clips/Video</div>
          <div>Durasi</div>
          <div>Aksi</div>
        </div>

        {(data || []).map((c) => (
          <div key={c.id} className="grid grid-cols-7 gap-2 p-3 text-sm border-b last:border-b-0 items-center">
            <div className="font-medium truncate">{c.name}</div>
            <div className="col-span-2 font-mono text-xs truncate">{c.youtube_channel_id}</div>
            <div>
              {c.is_active ? (
                <StatusBadge status="READY" />
              ) : (
                <StatusBadge status="PENDING" />
              )}
            </div>
            <div>{c.clips_per_video}</div>
            <div>
              {c.min_clip_sec}–{c.max_clip_sec}s
            </div>
            <div className="flex gap-1">
              <button
                onClick={() => setEditingChannel(c)}
                className="rounded px-2 py-1 text-xs border hover:bg-muted"
                title="Edit"
              >
                Edit
              </button>
              <button
                onClick={() => setBackfillChannel(c)}
                className="rounded px-2 py-1 text-xs border hover:bg-muted"
                title="Backfill Video Lama"
              >
                Backfill
              </button>
              <button
                onClick={() => handleDelete(c)}
                disabled={deleteMutation.isPending}
                className="rounded px-2 py-1 text-xs border text-red-600 hover:bg-red-50 disabled:opacity-50"
                title="Hapus"
              >
                Hapus
              </button>
            </div>
          </div>
        ))}

        {!isLoading && (data?.length ?? 0) === 0 && (
          <div className="p-6 text-center text-sm text-muted-foreground">
            Belum ada channel. Klik "+ Tambah Channel" untuk memulai.
          </div>
        )}
      </div>

      {/* Delete Error */}
      {deleteMutation.error && (
        <div className="text-sm text-red-500">
          Gagal menghapus: {String(deleteMutation.error)}
        </div>
      )}

      {/* Add Channel Dialog */}
      <AddChannelDialog
        open={showAddDialog}
        onClose={() => setShowAddDialog(false)}
      />

      {/* Add Video Dialog */}
      <AddVideoDialog
        open={showAddVideoDialog}
        onClose={() => setShowAddVideoDialog(false)}
      />

      {/* Backfill Dialog */}
      <BackfillDialog
        channel={backfillChannel}
        open={!!backfillChannel}
        onClose={() => setBackfillChannel(null)}
      />

      {/* Edit Channel Dialog */}
      <EditChannelDialog
        channel={editingChannel}
        open={!!editingChannel}
        onClose={() => setEditingChannel(null)}
      />
    </div>
  );
}
