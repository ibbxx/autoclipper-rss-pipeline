import { VIDEO_STATUS, RENDER_STATUS, POST_STATUS } from "@/lib/constants";
import type { VideoStatus, RenderStatus, PostStatus } from "@/lib/constants";

type StatusType = VideoStatus | RenderStatus | PostStatus;

// Use a function to get colors based on status value to avoid duplicate key issues
function getStatusColor(status: StatusType): string {
    // Success states
    if (status === "READY" || status === "POSTED") {
        return "bg-emerald-50 text-emerald-700 border-emerald-200";
    }

    // Error states
    if (status === "ERROR" || status === "FAILED") {
        return "bg-red-50 text-red-700 border-red-200";
    }

    // Processing states
    if (status === "PROCESSING" || status === "DOWNLOADING" || status === "RENDERING" || status === "UPLOADING") {
        return "bg-blue-50 text-blue-700 border-blue-200";
    }

    // Pending states (NEW, PENDING, QUEUED)
    return "bg-gray-50 text-gray-700 border-gray-200";
}

interface StatusBadgeProps {
    status: StatusType;
    className?: string;
}

export function StatusBadge({ status, className = "" }: StatusBadgeProps) {
    const colorClass = getStatusColor(status);

    return (
        <span
            className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium ${colorClass} ${className}`}
        >
            {status}
        </span>
    );
}
