import type { Metadata } from "next";
import { IBM_Plex_Mono, Sora } from "next/font/google";
import "./globals.css";

const sora = Sora({
  subsets: ["latin"],
  variable: "--font-sora",
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-mono",
  display: "swap",
});

import { AppQueryProvider } from "@/app/providers/query-provider";
import { AppLayout } from "@/shared/components/layout/AppLayout";

export const metadata: Metadata = {
  title: "CortexDocs ∞ | Sovereign Intelligence",
  description:
    "Production-grade, fully observable multi-document AI retrieval engine.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang='en'>
      <body
        className={`${sora.variable} ${plexMono.variable} antialiased font-sans bg-background text-foreground`}
      >
        <AppQueryProvider>
          <AppLayout>{children}</AppLayout>
        </AppQueryProvider>
      </body>
    </html>
  );
}
