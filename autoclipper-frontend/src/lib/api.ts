const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "";

type RequestOptions = RequestInit & { json?: unknown; timeout?: number };

// Custom error class for API errors
export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public isNetworkError: boolean = false
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  // Create AbortController for timeout
  const controller = new AbortController();
  const timeout = options.timeout || 30000; // 30 second default timeout
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const res = await fetch(url, {
      ...options,
      headers,
      body: options.json ? JSON.stringify(options.json) : options.body,
      cache: "no-store",
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new ApiError(
        `API Error ${res.status}: ${text || res.statusText}`,
        res.status,
        false
      );
    }

    return (await res.json()) as T;
  } catch (error) {
    clearTimeout(timeoutId);

    // Handle abort/timeout
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError(
        `Request timeout: Backend tidak merespon dalam ${timeout / 1000} detik. Pastikan server running dan tidak overloaded.`,
        undefined,
        true
      );
    }

    // Handle network errors (Failed to fetch)
    if (error instanceof TypeError && error.message === "Failed to fetch") {
      throw new ApiError(
        `Gagal terhubung ke backend (${BASE_URL || "localhost"}). Pastikan: 1) Backend running, 2) Port tidak diblokir, 3) CORS dikonfigurasi dengan benar.`,
        undefined,
        true
      );
    }

    // Re-throw ApiErrors
    if (error instanceof ApiError) {
      throw error;
    }

    // Handle other errors
    throw new ApiError(
      `Unexpected error: ${error instanceof Error ? error.message : String(error)}`,
      undefined,
      false
    );
  }
}
