import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CortexDocs ∞ — AI Retrieval Engine",
  description:
    "Production-grade, fully observable, resilient multi-document AI retrieval engine",
};

import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang='en'>
      <head>
        <link rel='preconnect' href='https://fonts.googleapis.com' />
        <link
          rel='preconnect'
          href='https://fonts.gstatic.com'
          crossOrigin='anonymous'
        />
        <link
          href='https://fonts.googleapis.com/css2?family=Inter:wght@100;200;300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap'
          rel='stylesheet'
        />
      </head>
      <body className='antialiased font-sans bg-white text-gray-900'>
        <Navbar />
        <main className='min-h-screen'>{children}</main>
        <Footer />
      </body>
    </html>
  );
}
