#!/usr/bin/env bash
set -euo pipefail

# =========================
# Auto Clipper Frontend (Next.js) - Full Scaffold
# Stack: Next.js (App Router) + TypeScript + Tailwind + shadcn/ui + TanStack Query
# =========================

APP_NAME="autoclipper-frontend"
PKG_MANAGER="npm"   # change to "pnpm" if you prefer

echo "==> 1) Create Next.js app: $APP_NAME"
if [ -d "$APP_NAME" ]; then
  echo "Folder '$APP_NAME' already exists. Remove it or change APP_NAME."
  exit 1
fi

npx create-next-app@latest "$APP_NAME" \
  --ts \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --import-alias "@/*" \
  --use-npm

cd "$APP_NAME"

echo "==> 2) Install dependencies (TanStack Query, RHF, Zod, clsx, tailwind-merge)"
$PKG_MANAGER install @tanstack/react-query @tanstack/react-query-devtools react-hook-form zod clsx tailwind-merge

echo "==> 3) (Optional but recommended) Init shadcn/ui"
echo "NOTE: shadcn init may prompt you; if it does, accept defaults and choose Tailwind + app router."
set +e
npx shadcn@latest init -y >/dev/null 2>&1
SHADCN_INIT_EXIT=$?
set -e
if [ $SHADCN_INIT_EXIT -ne 0 ]; then
  echo "!! shadcn init didn't run silently (maybe interactive / CLI changed)."
  echo "   Run manually after this script:"
  echo "   npx shadcn@latest init"
fi

echo "==> 4) Add common shadcn components (button, card, badge, table, dialog, checkbox, select, toast, progress)"
set +e
npx shadcn@latest add button card badge table dialog checkbox select toast progress separator input textarea dropdown-menu >/dev/null 2>&1
SHADCN_ADD_EXIT=$?
set -e
if [ $SHADCN_ADD_EXIT -ne 0 ]; then
  echo "!! shadcn add didn't run silently (maybe interactive / CLI changed)."
  echo "   You can run these manually later:"
  echo "   npx shadcn@latest add button card badge table dialog checkbox select toast progress separator input textarea dropdown-menu"
fi

echo "==> 5) Create project structure (app routes + components + lib)"
mkdir -p src/app/\(auth\)/login
mkdir -p src/app/\(dashboard\)/channels
mkdir -p src/app/\(dashboard\)/videos
mkdir -p src/app/\(dashboard\)/videos/[videoId]
mkdir -p src/app/\(dashboard\)/clips
mkdir -p src/app/\(dashboard\)/clips/[videoId]
mkdir -p src/app/\(dashboard\)/posts
mkdir -p src/components/layout
mkdir -p src/components/channels
mkdir -p src/components/videos
mkdir -p src/components/clips
mkdir -p src/components/posts
mkdir -p src/lib
mkdir -p src/hooks

echo "==> 6) Add environment example"
cat > .env.local.example <<'EOF'
# Backend API base URL (your FastAPI/Node backend)
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
EOF

echo "==> 7) Add lib: types, endpoints, api wrapper"
cat > src/lib/types.ts <<'EOF'
export type Channel = {
  id: string;
  name: string;
  youtube_channel_id: string;
  is_active: boolean;
  clips_per_video: number; // 3-4
  min_clip_sec: number;    // 20
  max_clip_sec: number;    // 45
  created_at: string;
};

export type Video = {
  id: string;
  channel_id: string;
  youtube_video_id: string;
  title: string;
  published_at: string;
  status: "NEW" | "DOWNLOADING" | "PROCESSING" | "READY" | "ERROR";
  progress?: number; // 0-100
  error_message?: string;
  created_at: string;
};

export type Clip = {
  id: string;
  video_id: string;
  start_sec: number;
  end_sec: number;
  score: number;
  file_url: string;        // mp4
  thumb_url: string;       // jpg
  subtitle_srt_url?: string;
  suggested_caption?: string;
  approved: boolean;
  render_status: "PENDING" | "RENDERING" | "READY" | "ERROR";
};

export type PostJob = {
  id: string;
  clip_id: string;
  status: "QUEUED" | "UPLOADING" | "PROCESSING" | "POSTED" | "FAILED";
  mode: "DRAFT" | "DIRECT";
  error_message?: string;
  created_at: string;
};
EOF

cat > src/lib/endpoints.ts <<'EOF'
export const endpoints = {
  channels: "/api/channels",
  videos: "/api/videos",
  video: (id: string) => `/api/videos/${id}`,
  clipsByVideo: (videoId: string) => `/api/videos/${videoId}/clips`,
  clip: (id: string) => `/api/clips/${id}`,
  approveVideoClips: (videoId: string) => `/api/videos/${videoId}/approve`,
  posts: "/api/posts",
  post: (id: string) => `/api/posts/${id}`,
};
EOF

cat > src/lib/api.ts <<'EOF'
const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "";

type RequestOptions = RequestInit & { json?: unknown };

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  const res = await fetch(url, {
    ...options,
    headers,
    body: options.json ? JSON.stringify(options.json) : options.body,
    cache: "no-store",
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }

  return (await res.json()) as T;
}
EOF

echo "==> 8) Add TanStack Query provider"
cat > src/components/QueryProvider.tsx <<'EOF'
"use client";

import * as React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [client] = React.useState(() => new QueryClient());
  return (
    <QueryClientProvider client={client}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
EOF

echo "==> 9) Layout components (Sidebar + Topbar)"
cat > src/components/layout/Sidebar.tsx <<'EOF'
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const nav = [
  { href: "/", label: "Overview" },
  { href: "/channels", label: "Channels" },
  { href: "/videos", label: "Videos" },
  { href: "/clips", label: "Clips" },
  { href: "/posts", label: "Posts" },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="w-64 border-r bg-background p-4">
      <div className="mb-6 text-lg font-semibold">Auto Clipper</div>
      <nav className="space-y-1">
        {nav.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={[
                "block rounded-md px-3 py-2 text-sm",
                active ? "bg-muted font-medium" : "hover:bg-muted/60",
              ].join(" ")}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
EOF

cat > src/components/layout/Topbar.tsx <<'EOF'
"use client";

export function Topbar() {
  return (
    <div className="flex h-14 items-center justify-between border-b bg-background px-4">
      <div className="text-sm text-muted-foreground">TikTok output preset: 9:16 (1080×1920)</div>
      <div className="text-sm">Operator</div>
    </div>
  );
}
EOF

echo "==> 10) Root layout uses QueryProvider + dashboard layout"
cat > src/app/layout.tsx <<'EOF'
import "./globals.css";
import type { Metadata } from "next";
import { QueryProvider } from "@/components/QueryProvider";

export const metadata: Metadata = {
  title: "Auto Clipper Dashboard",
  description: "Monitor YouTube -> Auto clips -> Approve -> Upload TikTok",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
EOF

cat > 'src/app/(dashboard)/layout.tsx' <<'EOF'
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background">
      <div className="flex">
        <Sidebar />
        <div className="flex-1">
          <Topbar />
          <main className="p-6">{children}</main>
        </div>
      </div>
    </div>
  );
}
EOF

echo "==> 11) Overview page"
cat > 'src/app/(dashboard)/page.tsx' <<'EOF'
export default function OverviewPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Overview</h1>
      <div className="grid gap-4 md:grid-cols-4">
        <div className="rounded-lg border p-4">
          <div className="text-sm text-muted-foreground">Active Channels</div>
          <div className="mt-2 text-2xl font-semibold">—</div>
        </div>
        <div className="rounded-lg border p-4">
          <div className="text-sm text-muted-foreground">Videos Today</div>
          <div className="mt-2 text-2xl font-semibold">—</div>
        </div>
        <div className="rounded-lg border p-4">
          <div className="text-sm text-muted-foreground">Clips Ready</div>
          <div className="mt-2 text-2xl font-semibold">—</div>
        </div>
        <div className="rounded-lg border p-4">
          <div className="text-sm text-muted-foreground">Upload Success</div>
          <div className="mt-2 text-2xl font-semibold">—</div>
        </div>
      </div>

      <div className="rounded-lg border p-4">
        <div className="text-sm font-medium">Recent Activity</div>
        <div className="mt-3 text-sm text-muted-foreground">
          Hook this up to backend logs later.
        </div>
      </div>
    </div>
  );
}
EOF

echo "==> 12) Channels page (UI shell + placeholder)"
cat > 'src/app/(dashboard)/channels/page.tsx' <<'EOF'
"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import type { Channel } from "@/lib/types";

export default function ChannelsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["channels"],
    queryFn: () => apiFetch<Channel[]>(endpoints.channels),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Channels</h1>
          <p className="text-sm text-muted-foreground">
            Add a YouTube channel ID. Default output: TikTok 9:16 (1080×1920), 3–4 clips/video.
          </p>
        </div>
        <button className="rounded-md border px-3 py-2 text-sm hover:bg-muted">
          + Add Channel
        </button>
      </div>

      {isLoading && <div className="text-sm text-muted-foreground">Loading…</div>}
      {error && <div className="text-sm text-red-500">{String(error)}</div>}

      <div className="rounded-lg border">
        <div className="grid grid-cols-6 gap-2 border-b p-3 text-xs font-medium text-muted-foreground">
          <div>Name</div>
          <div className="col-span-2">YouTube Channel ID</div>
          <div>Active</div>
          <div>Clips/Video</div>
          <div>Duration</div>
        </div>

        {(data || []).map((c) => (
          <div key={c.id} className="grid grid-cols-6 gap-2 p-3 text-sm">
            <div className="font-medium">{c.name}</div>
            <div className="col-span-2 font-mono text-xs">{c.youtube_channel_id}</div>
            <div>{c.is_active ? "Yes" : "No"}</div>
            <div>{c.clips_per_video}</div>
            <div>
              {c.min_clip_sec}–{c.max_clip_sec}s
            </div>
          </div>
        ))}

        {!isLoading && (data?.length ?? 0) === 0 && (
          <div className="p-4 text-sm text-muted-foreground">
            No channels yet. Click "Add Channel".
          </div>
        )}
      </div>
    </div>
  );
}
EOF

echo "==> 13) Videos page (UI shell + placeholder)"
cat > 'src/app/(dashboard)/videos/page.tsx' <<'EOF'
"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import type { Video } from "@/lib/types";
import Link from "next/link";

function badge(status: Video["status"]) {
  const base = "inline-flex items-center rounded-md border px-2 py-0.5 text-xs";
  switch (status) {
    case "READY": return `${base} bg-emerald-50`;
    case "ERROR": return `${base} bg-red-50`;
    default: return base;
  }
}

export default function VideosPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["videos"],
    queryFn: () => apiFetch<Video[]>(endpoints.videos),
    refetchInterval: 30000,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Videos</h1>
        <p className="text-sm text-muted-foreground">
          New uploads detected from your monitored channels.
        </p>
      </div>

      {isLoading && <div className="text-sm text-muted-foreground">Loading…</div>}
      {error && <div className="text-sm text-red-500">{String(error)}</div>}

      <div className="rounded-lg border">
        <div className="grid grid-cols-6 gap-2 border-b p-3 text-xs font-medium text-muted-foreground">
          <div className="col-span-3">Title</div>
          <div>Published</div>
          <div>Status</div>
          <div>Action</div>
        </div>

        {(data || []).map((v) => (
          <div key={v.id} className="grid grid-cols-6 gap-2 p-3 text-sm">
            <div className="col-span-3 font-medium">{v.title}</div>
            <div className="text-xs">{new Date(v.published_at).toLocaleString()}</div>
            <div><span className={badge(v.status)}>{v.status}</span></div>
            <div>
              <Link className="text-sm underline" href={`/videos/${v.id}`}>
                Open
              </Link>
            </div>
          </div>
        ))}

        {!isLoading && (data?.length ?? 0) === 0 && (
          <div className="p-4 text-sm text-muted-foreground">
            No videos yet.
          </div>
        )}
      </div>
    </div>
  );
}
EOF

echo "==> 14) Video detail page + link to clips review"
cat > 'src/app/(dashboard)/videos/[videoId]/page.tsx' <<'EOF'
"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import type { Video } from "@/lib/types";
import Link from "next/link";
import { useParams } from "next/navigation";

export default function VideoDetailPage() {
  const params = useParams<{ videoId: string }>();
  const videoId = params.videoId;

  const { data, isLoading, error } = useQuery({
    queryKey: ["video", videoId],
    queryFn: () => apiFetch<Video>(endpoints.video(videoId)),
    refetchInterval: 15000,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Video Detail</h1>
          <p className="text-sm text-muted-foreground">Status & processing timeline.</p>
        </div>
        <div className="flex gap-2">
          <Link className="rounded-md border px-3 py-2 text-sm hover:bg-muted" href={`/clips/${videoId}`}>
            Open Clips Review
          </Link>
          <button className="rounded-md border px-3 py-2 text-sm hover:bg-muted">
            Reprocess (placeholder)
          </button>
        </div>
      </div>

      {isLoading && <div className="text-sm text-muted-foreground">Loading…</div>}
      {error && <div className="text-sm text-red-500">{String(error)}</div>}

      {data && (
        <div className="rounded-lg border p-4 space-y-2">
          <div className="text-sm"><span className="text-muted-foreground">Title:</span> {data.title}</div>
          <div className="text-sm"><span className="text-muted-foreground">Status:</span> {data.status}</div>
          <div className="text-sm"><span className="text-muted-foreground">Published:</span> {new Date(data.published_at).toLocaleString()}</div>
          {data.error_message && (
            <div className="text-sm text-red-500">{data.error_message}</div>
          )}
        </div>
      )}
    </div>
  );
}
EOF

echo "==> 15) Clips index page (simple router)"
cat > 'src/app/(dashboard)/clips/page.tsx' <<'EOF'
export default function ClipsIndexPage() {
  return (
    <div className="space-y-2">
      <h1 className="text-2xl font-semibold">Clips</h1>
      <p className="text-sm text-muted-foreground">
        Open a specific video (Videos → Open) then click "Open Clips Review".
      </p>
    </div>
  );
}
EOF

echo "==> 16) Clips Review page (Approve 1-click)"
cat > 'src/app/(dashboard)/clips/[videoId]/page.tsx' <<'EOF'
"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import type { Clip } from "@/lib/types";
import { useParams, useRouter } from "next/navigation";

function fmtDur(c: Clip) {
  return `${Math.max(0, c.end_sec - c.start_sec).toFixed(0)}s`;
}

export default function ClipsReviewPage() {
  const params = useParams<{ videoId: string }>();
  const videoId = params.videoId;
  const qc = useQueryClient();
  const router = useRouter();

  const { data, isLoading, error } = useQuery({
    queryKey: ["clips", videoId],
    queryFn: () => apiFetch<Clip[]>(endpoints.clipsByVideo(videoId)),
    refetchInterval: 20000,
  });

  const [selected, setSelected] = React.useState<Record<string, boolean>>({});
  const [mode, setMode] = React.useState<"DRAFT" | "DIRECT">("DRAFT");

  React.useEffect(() => {
    if (!data) return;
    // Default: select all READY clips
    const next: Record<string, boolean> = {};
    for (const c of data) next[c.id] = c.render_status === "READY";
    setSelected(next);
  }, [data]);

  const approveMutation = useMutation({
    mutationFn: async () => {
      const clip_ids = Object.entries(selected)
        .filter(([, v]) => v)
        .map(([id]) => id);
      return apiFetch<{ ok: boolean }>(endpoints.approveVideoClips(videoId), {
        method: "POST",
        json: { clip_ids, mode },
      });
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["clips", videoId] });
      router.push("/posts");
    },
  });

  const clips = data || [];
  const selectedCount = Object.values(selected).filter(Boolean).length;

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Clips Review</h1>
          <p className="text-sm text-muted-foreground">
            Review TikTok-ready clips (9:16). Select then approve to upload.
          </p>
        </div>
        <button
          className="rounded-md border px-3 py-2 text-sm hover:bg-muted"
          onClick={() => router.back()}
        >
          Back
        </button>
      </div>

      {isLoading && <div className="text-sm text-muted-foreground">Loading…</div>}
      {error && <div className="text-sm text-red-500">{String(error)}</div>}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {clips.map((c) => {
          const disabled = c.render_status !== "READY";
          return (
            <div key={c.id} className="rounded-xl border overflow-hidden">
              <div className="aspect-[9/16] bg-muted">
                {/* Thumbnail image (fallback if empty) */}
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={c.thumb_url || "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='540' height='960'%3E%3Crect width='100%25' height='100%25' fill='%23eee'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%23999'%3EThumbnail%3C/text%3E%3C/svg%3E"}
                  alt="thumb"
                  className="h-full w-full object-cover"
                />
              </div>
              <div className="p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={!!selected[c.id]}
                      disabled={disabled}
                      onChange={(e) => setSelected((s) => ({ ...s, [c.id]: e.target.checked }))}
                    />
                    Select
                  </label>
                  <div className="text-xs text-muted-foreground">
                    {fmtDur(c)} • Score {c.score.toFixed(0)}
                  </div>
                </div>

                <div className="text-xs text-muted-foreground">
                  Render: {c.render_status}
                </div>

                <div className="flex gap-2">
                  <a
                    className={[
                      "rounded-md border px-3 py-2 text-sm",
                      c.file_url ? "hover:bg-muted" : "pointer-events-none opacity-50",
                    ].join(" ")}
                    href={c.file_url || "#"}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Preview
                  </a>
                  <button
                    className="rounded-md border px-3 py-2 text-sm hover:bg-muted"
                    onClick={() => {
                      // placeholder: later implement inline caption editor
                      alert("Caption editor: coming soon");
                    }}
                  >
                    Edit Caption
                  </button>
                </div>
              </div>
            </div>
          );
        })}

        {!isLoading && clips.length === 0 && (
          <div className="text-sm text-muted-foreground">
            No clips yet. Wait for processing or reprocess the video.
          </div>
        )}
      </div>

      {/* Sticky approve bar */}
      <div className="sticky bottom-4 rounded-xl border bg-background p-4 shadow-sm">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="text-sm">
            Selected <span className="font-semibold">{selectedCount}</span> clips
          </div>

          <div className="flex items-center gap-2">
            <select
              className="h-9 rounded-md border bg-background px-2 text-sm"
              value={mode}
              onChange={(e) => setMode(e.target.value as "DRAFT" | "DIRECT")}
            >
              <option value="DRAFT">Upload as Draft (recommended)</option>
              <option value="DIRECT">Direct Post</option>
            </select>

            <button
              className="h-9 rounded-md border px-3 text-sm hover:bg-muted disabled:opacity-50"
              disabled={selectedCount === 0 || approveMutation.isPending}
              onClick={() => approveMutation.mutate()}
            >
              {approveMutation.isPending ? "Approving…" : "Approve & Upload"}
            </button>
          </div>
        </div>

        {approveMutation.error && (
          <div className="mt-2 text-sm text-red-500">{String(approveMutation.error)}</div>
        )}
      </div>
    </div>
  );
}
EOF

echo "==> 17) Posts page (upload log UI shell)"
cat > 'src/app/(dashboard)/posts/page.tsx' <<'EOF'
"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import type { PostJob } from "@/lib/types";

function badge(status: PostJob["status"]) {
  const base = "inline-flex items-center rounded-md border px-2 py-0.5 text-xs";
  switch (status) {
    case "POSTED": return `${base} bg-emerald-50`;
    case "FAILED": return `${base} bg-red-50`;
    default: return base;
  }
}

export default function PostsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["posts"],
    queryFn: () => apiFetch<PostJob[]>(endpoints.posts),
    refetchInterval: 15000,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Posts (Upload Log)</h1>
        <p className="text-sm text-muted-foreground">
          Track TikTok uploads (queued → uploading → posted).
        </p>
      </div>

      {isLoading && <div className="text-sm text-muted-foreground">Loading…</div>}
      {error && <div className="text-sm text-red-500">{String(error)}</div>}

      <div className="rounded-lg border">
        <div className="grid grid-cols-5 gap-2 border-b p-3 text-xs font-medium text-muted-foreground">
          <div>Clip ID</div>
          <div>Status</div>
          <div>Mode</div>
          <div>Created</div>
          <div>Error</div>
        </div>

        {(data || []).map((p) => (
          <div key={p.id} className="grid grid-cols-5 gap-2 p-3 text-sm">
            <div className="font-mono text-xs">{p.clip_id}</div>
            <div><span className={badge(p.status)}>{p.status}</span></div>
            <div className="text-xs">{p.mode}</div>
            <div className="text-xs">{new Date(p.created_at).toLocaleString()}</div>
            <div className="text-xs text-red-500 truncate">{p.error_message || ""}</div>
          </div>
        ))}

        {!isLoading && (data?.length ?? 0) === 0 && (
          <div className="p-4 text-sm text-muted-foreground">
            No upload jobs yet.
          </div>
        )}
      </div>
    </div>
  );
}
EOF

echo "==> 18) Auth: simple login page"
cat > 'src/app/(auth)/login/page.tsx' <<'EOF'
"use client";

import { useRouter } from "next/navigation";
import * as React from "react";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="w-full max-w-sm rounded-xl border p-6 space-y-4">
        <h1 className="text-xl font-semibold">Login</h1>
        <p className="text-sm text-muted-foreground">MVP auth placeholder.</p>
        <input
          className="w-full rounded-md border px-3 py-2 text-sm"
          placeholder="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          className="w-full rounded-md border px-3 py-2 text-sm"
          placeholder="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button
          className="w-full rounded-md border px-3 py-2 text-sm hover:bg-muted"
          onClick={() => {
            // Dummy login: store token placeholder
            localStorage.setItem("token", "dev-token");
            router.push("/");
          }}
        >
          Sign in
        </button>
      </div>
    </div>
  );
}
EOF

echo "==> 19) Add a simple redirect from / to dashboard layout (already at /(dashboard)/page.tsx)"
# Nothing else needed; App Router will render /(dashboard)/page.tsx at "/"

echo "==> 20) Done."
echo ""
echo "Next steps:"
echo "1) Copy env file: cp .env.local.example .env.local and set NEXT_PUBLIC_API_BASE_URL"
echo "2) Run dev server: npm run dev"
echo ""
echo "Notes:"
echo "- If shadcn init/add didn't run, execute them manually."
echo "- Backend endpoints are placeholders. Frontend expects routes like /api/channels, /api/videos, etc."
