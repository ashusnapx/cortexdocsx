import Link from "next/link";

const FOOTER_LINKS = [
  { label: "Workspace", href: "/#workspace" },
  { label: "Highlights", href: "/#highlights" },
  { label: "System Design", href: "/system-design" },
];

export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className='border-t border-slate-200/80 bg-white/55'>
      <div className='container-main py-8'>
        <div className='flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between'>
          <div>
            <p className='text-sm font-semibold text-slate-900'>CortexDocs</p>
            <p className='text-sm text-slate-500'>
              Retrieval interface rebuilt with Tailwind + shadcn-style components.
            </p>
          </div>

          <div className='flex flex-wrap items-center gap-4'>
            {FOOTER_LINKS.map((link) => (
              <Link
                key={link.label}
                href={link.href}
                className='text-sm font-medium text-slate-500 transition-colors hover:text-slate-900'
              >
                {link.label}
              </Link>
            ))}
          </div>
        </div>

        <p className='mt-6 text-xs text-slate-400'>© {year} CortexDocs. All rights reserved.</p>
      </div>
    </footer>
  );
}
