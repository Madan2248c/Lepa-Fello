import { useAuth } from "@clerk/nextjs";
import { useCallback } from "react";
import { apiFetch } from "@/lib/api";

export function useApiFetch() {
  const { getToken } = useAuth();

  return useCallback(
    async (path: string, tenantId: string | null, options?: RequestInit) => {
      const token = await getToken();
      return apiFetch(path, tenantId, { ...options, token });
    },
    [getToken]
  );
}
