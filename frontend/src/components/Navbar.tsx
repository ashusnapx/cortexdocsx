import Link from "next/link";
import { Blocks, LayoutPanelTop, Rocket } from "lucide-react";

const NAV_LINKS = [
  { label: "Workspace", href: "/#workspace" },
  { label: "Highlights", href: "/#highlights" },
  { label: "System Design", href: "/system-design" },
];

export function Navbar() {
  return (
    <header className='sticky top-0 z-50 border-b border-white/60 bg-[#f8f6ef]/75 backdrop-blur-xl'>
      <div className='container-main flex h-16 items-center justify-between'>
        <Link href='/' className='inline-flex items-center gap-3'>
          <span className='inline-flex h-9 w-9 items-center justify-center rounded-xl bg-slate-900 text-white shadow-[0_8px_18px_rgba(15,23,42,0.2)]'>
            <Blocks className='h-4 w-4' />
          </span>
          <span className='text-sm font-semibold uppercase tracking-[0.18em] text-slate-900'>
            CortexDocs
          </span>
        </Link>

        <nav className='hidden items-center gap-6 md:flex'>
          {NAV_LINKS.map((link) => (
            <Link
              key={link.label}
              href={link.href}
              className='text-sm font-medium text-slate-600 transition-colors hover:text-slate-900'
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className='flex items-center gap-2'>
          <Link
            href='/system-design'
            className='hidden rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 transition-colors hover:bg-white md:inline-flex'
          >
            <LayoutPanelTop className='mr-1.5 h-3.5 w-3.5' />
            Architecture
          </Link>
          <Link
            href='/#workspace'
            className='inline-flex items-center rounded-lg bg-teal-600 px-3 py-2 text-xs font-semibold text-white transition-colors hover:bg-teal-700'
          >
            <Rocket className='mr-1.5 h-3.5 w-3.5' />
            Open Console
          </Link>
        </div>
      </div>
    </header>
  );
}
