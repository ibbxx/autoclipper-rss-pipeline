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
