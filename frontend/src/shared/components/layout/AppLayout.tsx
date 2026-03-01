"use client";

import { Navbar } from "../Navbar";
import { Footer } from "../Footer";
import { Toaster } from "@/shared/ui/toast";
import { ErrorBoundary } from "@/core/error-handling/ErrorBoundary";

interface AppLayoutProps {
  children: React.ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className='flex min-h-screen flex-col bg-background text-foreground font-sans antialiased'>
      <Navbar />
      <ErrorBoundary>
        <main className='flex-1'>{children}</main>
      </ErrorBoundary>
      <Footer />
      <Toaster position='bottom-right' />
    </div>
  );
}
