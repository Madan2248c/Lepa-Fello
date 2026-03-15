"use client";

import { useAuth } from "@clerk/nextjs";

/**
 * Returns the tenant ID for API calls.
 * Uses userId (each user is their own tenant).
 */
export function useTenantId(): string | null {
  const { userId } = useAuth();
  if (userId) return `user_${userId}`;
  return null;
}
