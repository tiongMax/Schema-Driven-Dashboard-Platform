const API_URL = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? "/api";

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
  }
}

function detailToMessage(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object") {
    const value = detail as Record<string, unknown>;
    if (typeof value.message === "string") {
      const nested = value.row_errors ?? value.errors;
      if (Array.isArray(nested)) {
        const messages = nested.flatMap((item) => {
          if (!item || typeof item !== "object") return [];
          const error = item as Record<string, unknown>;
          const location = typeof error.view_index === "number"
            ? `View ${error.view_index + 1}`
            : typeof error.row_index === "number"
              ? `Row ${error.row_index + 1}`
              : "Request";
          const field = typeof error.field === "string" ? `, ${error.field}` : "";
          if (Array.isArray(error.errors)) {
            return error.errors.map((child) => {
              if (!child || typeof child !== "object") return `${location}: invalid value`;
              const childError = child as Record<string, unknown>;
              const childField = typeof childError.field === "string" ? `, ${childError.field}` : "";
              return `${location}${childField}: ${String(childError.message ?? "invalid value")}`;
            });
          }
          return [`${location}${field}: ${String(error.message ?? "invalid value")}`];
        });
        return messages.length ? `${value.message}. ${messages.join(" • ")}` : value.message;
      }
      return value.message;
    }
  }
  return "The server could not process this request.";
}

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(detailToMessage(body?.detail), response.status);
  }
  return body as T;
}
