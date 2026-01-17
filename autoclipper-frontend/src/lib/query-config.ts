"use client";

import { ApiError } from "@/lib/api";

// Retry configuration for React Query
export const RETRY_CONFIG = {
    // Retry up to 3 times for network errors
    retry: (failureCount: number, error: Error) => {
        // Don't retry if it's a client error (4xx)
        if (error instanceof ApiError && error.status && error.status >= 400 && error.status < 500) {
            return false;
        }
        // Retry network errors up to 3 times
        if (error instanceof ApiError && error.isNetworkError) {
            return failureCount < 3;
        }
        // Default: retry up to 2 times
        return failureCount < 2;
    },

    // Exponential backoff: 1s, 2s, 4s...
    retryDelay: (attemptIndex: number) => Math.min(1000 * 2 ** attemptIndex, 30000),
};

// Default query options with retry
export const DEFAULT_QUERY_OPTIONS = {
    ...RETRY_CONFIG,
    staleTime: 5000, // Consider data stale after 5 seconds
};
