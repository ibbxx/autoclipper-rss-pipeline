"use client";

import { useQuery } from "@tanstack/react-query";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "";

type HealthStatus = {
    isOnline: boolean;
    latency: number | null;
    lastChecked: Date | null;
    error: string | null;
};

async function checkHealth(): Promise<HealthStatus> {
    const start = Date.now();

    try {
        const response = await fetch(`${BASE_URL}/health`, {
            method: "GET",
            cache: "no-store",
            signal: AbortSignal.timeout(5000), // 5 second timeout
        });

        const latency = Date.now() - start;

        if (response.ok) {
            return {
                isOnline: true,
                latency,
                lastChecked: new Date(),
                error: null,
            };
        }

        return {
            isOnline: false,
            latency: null,
            lastChecked: new Date(),
            error: `Server returned ${response.status}`,
        };
    } catch (error) {
        return {
            isOnline: false,
            latency: null,
            lastChecked: new Date(),
            error: error instanceof TypeError
                ? "Cannot connect to backend server"
                : String(error),
        };
    }
}

export function useHealthCheck(enabled: boolean = true) {
    return useQuery({
        queryKey: ["health"],
        queryFn: checkHealth,
        enabled,
        refetchInterval: 10000, // Check every 10 seconds
        retry: false, // Don't retry health checks
        staleTime: 5000,
    });
}
