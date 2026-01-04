export const endpoints = {
  channels: "/api/channels",
  channel: (id: string) => `/api/channels/${id}`,
  resolveChannel: "/api/channels/resolve",
  videos: "/api/videos",
  video: (id: string) => `/api/videos/${id}`,
  clipsByVideo: (videoId: string) => `/api/videos/${videoId}/clips`,
  clip: (id: string) => `/api/clips/${id}`,
  approveVideoClips: (videoId: string) => `/api/videos/${videoId}/approve`,
  posts: "/api/posts",
  post: (id: string) => `/api/posts/${id}`,
  backfillChannel: (id: string, count: number) => `/api/channels/${id}/backfill?count=${count}`,
};
