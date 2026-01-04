import type { Clip } from "@/lib/types";
import { PLACEHOLDER_THUMBNAIL } from "@/lib/constants";

interface ClipCardProps {
    clip: Clip;
    selected: boolean;
    disabled: boolean;
    onSelect: (checked: boolean) => void;
    onEditCaption?: () => void;
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

function getFullUrl(path?: string) {
    if (!path) return undefined;
    if (path.startsWith("http")) return path;
    const base = API_BASE.replace(/\/+$/, ""); // remove trailing slash
    const cleanPath = path.replace(/^\/+/, ""); // remove leading slash
    return `${base}/${cleanPath}`;
}

export function ClipCard({
    clip,
    selected,
    disabled,
    onSelect,
    onEditCaption,
}: ClipCardProps) {
    const duration = Math.max(0, clip.end_sec - clip.start_sec).toFixed(0);
    const thumbUrl = getFullUrl(clip.thumb_url) || PLACEHOLDER_THUMBNAIL;
    const fileUrl = getFullUrl(clip.file_url);

    return (
        <div className="rounded-xl border overflow-hidden">
            {/* Thumbnail */}
            <div className="aspect-[9/16] bg-muted relative group">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                    src={thumbUrl}
                    alt={`Clip thumbnail`}
                    className="h-full w-full object-cover"
                />

                {/* Play Button Overlay (Optional - could integrate actual video player here) */}
                {fileUrl && (
                    <a
                        href={fileUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 bg-black/30 transition-opacity"
                    >
                        <div className="bg-white/90 rounded-full p-3 shadow-lg">
                            <svg className="w-6 h-6 text-black" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M8 5v14l11-7z" />
                            </svg>
                        </div>
                    </a>
                )}
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
                        className={`rounded-md border px-3 py-2 text-sm flex-1 text-center ${fileUrl
                            ? "hover:bg-muted"
                            : "pointer-events-none opacity-50"
                            }`}
                        href={fileUrl || "#"}
                        target="_blank"
                        rel="noreferrer"
                    >
                        Preview Video
                    </a>
                    {onEditCaption && (
                        <button
                            className="rounded-md border px-3 py-2 text-sm hover:bg-muted"
                            onClick={onEditCaption}
                        >
                            Edit
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
