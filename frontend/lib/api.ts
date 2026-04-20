/** Default: same-origin rewrite → FastAPI (see next.config.mjs). Override with NEXT_PUBLIC_API_URL for direct calls. */
const RAW = process.env.NEXT_PUBLIC_API_URL?.trim();
export const API = RAW ? RAW.replace(/\/$/, "") : "/api/backend";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiFetch<T>(
  path: string,
  accessToken: string,
  init: RequestInit = {},
): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
        ...init.headers,
      },
    });
  } catch (e) {
    const hint =
      API.startsWith("http")
        ? `Confira se a API está no ar (${API}/health) e CORS.`
        : `Confira se o backend está no ar e reinicie o Next após mudar BACKEND_INTERNAL_URL (proxy ${API}).`;
    throw new Error(
      e instanceof Error && e.message === "Failed to fetch"
        ? `Não foi possível contatar a API. ${hint}`
        : e instanceof Error
          ? e.message
          : "Falha de rede",
    );
  }
  if (!res.ok) {
    const raw = await res.text();
    let msg = raw || res.statusText;
    try {
      const j = JSON.parse(raw) as { detail?: unknown };
      if (typeof j.detail === "string") {
        msg = j.detail;
      }
    } catch {
      /* use raw text */
    }
    throw new ApiError(res.status, msg);
  }
  return (await res.json()) as T;
}
