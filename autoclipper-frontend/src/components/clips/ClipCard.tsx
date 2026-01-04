import type { Clip } from "@/lib/types";
import { PLACEHOLDER_THUMBNAIL } from "@/lib/constants";

interface ClipCardProps {
    clip: Clip;
    selected: boolean;
    disabled: boolean;
    onSelect: (checked: boolean) => void;
    onEditCaption?: () => void;
}

export function ClipCard({
    clip,
    selected,
    disabled,
    onSelect,
    onEditCaption,
}: ClipCardProps) {
    const duration = Math.max(0, clip.end_sec - clip.start_sec).toFixed(0);

    return (
        <div className="rounded-xl border overflow-hidden">
            {/* Thumbnail */}
            <div className="aspect-[9/16] bg-muted">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                    src={clip.thumb_url || PLACEHOLDER_THUMBNAIL}
                    alt={`Clip thumbnail`}
                    className="h-full w-full object-cover"
                />
            </div>

            {/* Content */}
            <div className="p-3 space-y-2">
                {/* Selection row */}
                <div className="flex items-center justify-between">
                    <label className="flex items-center gap-2 text-sm cursor-pointer">
                        <input
                            type="checkbox"
                            checked={selected}
                            disabled={disabled}
                            onChange={(e) => onSelect(e.target.checked)}
                            className="rounded"
                        />
                        Select
                    </label>
                    <div className="text-xs text-muted-foreground">
                        {duration}s • Score {clip.score.toFixed(0)}
                    </div>
                </div>

                {/* Status */}
                <div className="text-xs text-muted-foreground">
                    Render: {clip.render_status}
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                    <a
                        className={`rounded-md border px-3 py-2 text-sm ${clip.file_url
                                ? "hover:bg-muted"
                                : "pointer-events-none opacity-50"
                            }`}
                        href={clip.file_url || "#"}
                        target="_blank"
                        rel="noreferrer"
                    >
                        Preview
                    </a>
                    {onEditCaption && (
                        <button
                            className="rounded-md border px-3 py-2 text-sm hover:bg-muted"
                            onClick={onEditCaption}
                        >
                            Edit Caption
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
