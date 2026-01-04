// Status constants
export const VIDEO_STATUS = {
    NEW: "NEW",
    DOWNLOADING: "DOWNLOADING",
    PROCESSING: "PROCESSING",
    READY: "READY",
    ERROR: "ERROR",
} as const;

export const RENDER_STATUS = {
    PENDING: "PENDING",
    RENDERING: "RENDERING",
    READY: "READY",
    ERROR: "ERROR",
} as const;

export const POST_STATUS = {
    QUEUED: "QUEUED",
    UPLOADING: "UPLOADING",
    PROCESSING: "PROCESSING",
    POSTED: "POSTED",
    FAILED: "FAILED",
} as const;

export const POST_MODE = {
    DRAFT: "DRAFT",
    DIRECT: "DIRECT",
} as const;

// Type definitions
export type VideoStatus = (typeof VIDEO_STATUS)[keyof typeof VIDEO_STATUS];
export type RenderStatus = (typeof RENDER_STATUS)[keyof typeof RENDER_STATUS];
export type PostStatus = (typeof POST_STATUS)[keyof typeof POST_STATUS];
export type PostMode = (typeof POST_MODE)[keyof typeof POST_MODE];

// UI constants
export const REFETCH_INTERVALS = {
    CLIPS: 20000,
    VIDEOS: 30000,
    POSTS: 15000,
    VIDEO_DETAIL: 15000,
} as const;

export const PLACEHOLDER_THUMBNAIL =
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='540' height='960'%3E%3Crect width='100%25' height='100%25' fill='%23eee'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%23999'%3EThumbnail%3C/text%3E%3C/svg%3E";
