"use client";

import { ConnectionStatus } from "./ConnectionStatus";

export function Topbar() {
  return (
    <div className="flex h-14 items-center justify-between border-b bg-background px-4">
      <div className="text-sm text-muted-foreground">TikTok output preset: 9:16 (1080×1920)</div>
      <div className="flex items-center gap-4">
        <ConnectionStatus />
        <div className="text-sm">Operator</div>
      </div>
    </div>
  );
}

