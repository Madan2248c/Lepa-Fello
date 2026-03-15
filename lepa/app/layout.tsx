import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "LEPA - Account Intelligence",
  description: "AI-powered account intelligence and enrichment system for sales teams",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body className={`${inter.variable} antialiased selection:bg-[#5B9BD5]/30 text-[#E8E9EA]`}>
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
