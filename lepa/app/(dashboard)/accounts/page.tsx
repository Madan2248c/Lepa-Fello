"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function AccountsRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/companies");
  }, [router]);
  return null;
}
