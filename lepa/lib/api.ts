/**
 * API client with tenant-scoped requests.
 * Passes X-Tenant-Id header (orgId or userId from Clerk) for multi-tenancy.
 * Passes Authorization: Bearer <clerk_token> for backend auth.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const AGENT_BASE = process.env.NEXT_PUBLIC_AGENT_URL || "http://localhost:8001";

export function getApiHeaders(tenantId: string | null, token?: string | null): HeadersInit {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (tenantId) headers["X-Tenant-Id"] = tenantId;
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

export async function apiFetch(
  path: string,
  tenantId: string | null,
  options?: RequestInit & { token?: string | null }
): Promise<Response> {
  const { token, ...rest } = options ?? {};
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  return fetch(url, {
    ...rest,
    headers: {
      ...getApiHeaders(tenantId, token),
      ...(rest?.headers as Record<string, string>),
    },
  });
}

export { API_BASE, AGENT_BASE };
