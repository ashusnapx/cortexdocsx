import Link from "next/link";
import { Zap } from "lucide-react";

export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className='w-full border-t border-border bg-surface'>
      <div className='mx-auto max-w-[1200px] px-6'>
        <div className='flex flex-col items-center justify-between gap-6 py-8 md:flex-row md:py-12'>
          {/* Logo */}
          <Link href='/' className='flex items-center gap-2.5 no-underline'>
            <div className='flex h-8 w-8 items-center justify-center rounded-lg bg-primary'>
              <Zap className='h-4 w-4 text-white' />
            </div>
            <span className='text-[15px] font-semibold tracking-tight text-foreground'>
              CortexDocs
            </span>
          </Link>

          {/* Copyright */}
          <p className='text-sm text-muted'>
            &copy; {year} CortexDocs. All rights reserved.
          </p>

          {/* Links */}
          <div className='flex items-center gap-6'>
            <Link
              href='#'
              className='text-sm text-muted transition-colors hover:text-foreground no-underline'
            >
              Privacy Policy
            </Link>
            <Link
              href='/system-design'
              className='text-sm text-muted transition-colors hover:text-foreground no-underline'
            >
              System Design
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
