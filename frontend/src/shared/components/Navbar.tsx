import Link from "next/link";
import { Zap } from "lucide-react";
import { cn } from "@/shared/utils/tw";

export function Navbar() {
  return (
    <nav className='sticky top-0 z-50 h-16 w-full border-b border-border bg-background/80 backdrop-blur-xl backdrop-saturate-[180%]'>
      <div className='mx-auto flex h-full max-w-[1200px] items-center justify-between px-6'>
        {/* Logo */}
        <Link href='/' className='group flex items-center gap-2.5 no-underline'>
          <div className='flex h-8 w-8 items-center justify-center rounded-lg bg-primary transition-transform group-hover:scale-105'>
            <Zap className='h-4 w-4 text-white' />
          </div>
          <span className='text-[15px] font-semibold tracking-tight text-foreground'>
            CortexDocs
          </span>
        </Link>

        {/* Center Nav */}
        <div className='hidden items-center gap-8 md:flex'>
          <Link
            href='#dashboard'
            className='text-sm font-medium text-muted transition-colors hover:text-foreground no-underline'
          >
            Dashboard
          </Link>
          <Link
            href='/system-design'
            className='text-sm font-medium text-muted transition-colors hover:text-foreground no-underline'
          >
            System Design
          </Link>
        </div>

        {/* Right Actions */}
        <div className='flex items-center gap-4'>
          <Link
            href='#dashboard'
            className={cn(
              "inline-flex h-9 items-center justify-center rounded-full bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primaryHover no-underline",
            )}
          >
            Get Started
          </Link>
        </div>
      </div>
    </nav>
  );
}
