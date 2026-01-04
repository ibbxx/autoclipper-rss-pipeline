"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useParams } from "next/navigation";
import { useClips, useApproveClips, useClipSelection } from "@/hooks/useClips";
import { ClipCard } from "@/components/clips/ClipCard";
import { PageHeader } from "@/components/layout/PageHeader";
import { POST_MODE } from "@/lib/constants";
import type { PostMode } from "@/lib/constants";

export default function ClipsReviewPage() {
  const params = useParams<{ videoId: string }>();
  const videoId = params.videoId;
  const router = useRouter();

  const { data: clips, isLoading, error } = useClips(videoId);
  const { selected, toggleClip, selectedIds, selectedCount } = useClipSelection(clips);
  const approveMutation = useApproveClips(videoId);

  const [mode, setMode] = useState<PostMode>(POST_MODE.DRAFT);

  const handleApprove = async () => {
    await approveMutation.mutateAsync({ clipIds: selectedIds, mode });
    router.push("/posts");
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Clips Review"
        description="Review TikTok-ready clips (9:16). Select then approve to upload."
        action={
          <button
            className="rounded-md border px-3 py-2 text-sm hover:bg-muted"
            onClick={() => router.back()}
          >
            Back
          </button>
        }
      />

      {/* Loading & Error States */}
      {isLoading && <div className="text-sm text-muted-foreground">Loading…</div>}
      {error && <div className="text-sm text-red-500">{String(error)}</div>}

      {/* Clips Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {(clips || []).map((clip) => (
          <ClipCard
            key={clip.id}
            clip={clip}
            selected={!!selected[clip.id]}
            disabled={clip.render_status !== "READY"}
            onSelect={(checked) => toggleClip(clip.id, checked)}
            onEditCaption={() => alert("Caption editor: coming soon")}
          />
        ))}

        {!isLoading && (clips?.length ?? 0) === 0 && (
          <div className="text-sm text-muted-foreground">
            No clips yet. Wait for processing or reprocess the video.
          </div>
        )}
      </div>

      {/* Approve Bar */}
      <ApproveBar
        selectedCount={selectedCount}
        mode={mode}
        onModeChange={setMode}
        onApprove={handleApprove}
        isPending={approveMutation.isPending}
        error={approveMutation.error}
      />
    </div>
  );
}

// Sub-component for the sticky approve bar
interface ApproveBarProps {
  selectedCount: number;
  mode: PostMode;
  onModeChange: (mode: PostMode) => void;
  onApprove: () => void;
  isPending: boolean;
  error: Error | null;
}

function ApproveBar({
  selectedCount,
  mode,
  onModeChange,
  onApprove,
  isPending,
  error,
}: ApproveBarProps) {
  return (
    <div className="sticky bottom-4 rounded-xl border bg-background p-4 shadow-sm">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="text-sm">
          Selected <span className="font-semibold">{selectedCount}</span> clips
        </div>

        <div className="flex items-center gap-2">
          <select
            className="h-9 rounded-md border bg-background px-2 text-sm"
            value={mode}
            onChange={(e) => onModeChange(e.target.value as PostMode)}
          >
            <option value={POST_MODE.DRAFT}>Upload as Draft (recommended)</option>
            <option value={POST_MODE.DIRECT}>Direct Post</option>
          </select>

          <button
            className="h-9 rounded-md border px-3 text-sm hover:bg-muted disabled:opacity-50"
            disabled={selectedCount === 0 || isPending}
            onClick={onApprove}
          >
            {isPending ? "Approving…" : "Approve & Upload"}
          </button>
        </div>
      </div>

      {error && (
        <div className="mt-2 text-sm text-red-500">{String(error)}</div>
      )}
    </div>
  );
}
