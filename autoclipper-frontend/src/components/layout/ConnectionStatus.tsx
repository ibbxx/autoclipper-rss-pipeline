"use client";

import { useHealthCheck } from "@/hooks/useHealthCheck";
import { cn } from "@/lib/utils";

export function ConnectionStatus() {
    const { data: health, isLoading } = useHealthCheck();

    if (isLoading) {
        return (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <div className="h-2 w-2 rounded-full bg-yellow-500 animate-pulse" />
                <span>Checking connection...</span>
            </div>
        );
    }

    if (!health?.isOnline) {
        return (
            <div className="flex items-center gap-2 text-xs">
                <div className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
                <span className="text-red-600 font-medium">
                    Backend Offline
                </span>
                {health?.error && (
                    <span className="text-muted-foreground hidden sm:inline">
                        — {health.error}
                    </span>
                )}
            </div>
        );
    }

    return (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <div className="h-2 w-2 rounded-full bg-green-500" />
            <span className="hidden sm:inline">Connected</span>
            {health.latency !== null && (
                <span className={cn(
                    "hidden md:inline",
                    health.latency > 500 ? "text-yellow-600" : ""
                )}>
                    ({health.latency}ms)
                </span>
            )}
        </div>
    );
}
