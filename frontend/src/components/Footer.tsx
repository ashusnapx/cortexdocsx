"use client";

import Link from "next/link";
import { Zap } from "lucide-react";

const FOOTER_COLS = [
  {
    title: "Platform",
    links: [
      { label: "Ingestion", href: "#dashboard" },
      { label: "Retrieval", href: "#dashboard" },
      { label: "Observability", href: "#dashboard" },
      { label: "System Design", href: "/system-design" },
    ],
  },
  {
    title: "Company",
    links: [
      { label: "About", href: "#" },
      { label: "Privacy", href: "#" },
      { label: "Security", href: "#" },
      { label: "Contact", href: "#" },
    ],
  },
  {
    title: "Resources",
    links: [
      { label: "Documentation", href: "/system-design" },
      { label: "API Reference", href: "#" },
      { label: "GitHub", href: "#" },
      { label: "Changelog", href: "#" },
    ],
  },
];

export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className='bg-[#f5f5f7] border-t border-gray-200/60'>
      <div className='max-w-[1200px] mx-auto px-6'>
        {/* Main */}
        <div className='py-16 grid grid-cols-1 md:grid-cols-2 gap-12'>
          {/* Left — Brand */}
          <div>
            <Link
              href='/'
              className='flex items-center gap-2.5 no-underline mb-5'
            >
              <div className='w-8 h-8 rounded-lg bg-black flex items-center justify-center'>
                <Zap className='w-4 h-4 text-white' />
              </div>
              <span className='text-[15px] font-semibold text-gray-900 tracking-tight'>
                CortexDocs
              </span>
            </Link>
            <p className='text-[22px] md:text-[28px] font-semibold leading-[1.3] tracking-tight text-gray-900 max-w-[360px]'>
              Transparent AI retrieval
              <br />
              <span className='text-gray-400'>you can trust.</span>
            </p>
          </div>

          {/* Right — Link Columns */}
          <div className='grid grid-cols-3 gap-6'>
            {FOOTER_COLS.map((col) => (
              <div key={col.title}>
                <p className='text-[12px] font-semibold uppercase tracking-[0.06em] text-gray-400 mb-4'>
                  {col.title}
                </p>
                <ul className='space-y-3 list-none p-0 m-0'>
                  {col.links.map((link) => (
                    <li key={link.label}>
                      <Link
                        href={link.href}
                        className='text-[14px] text-gray-500 no-underline hover:text-gray-900 transition-colors duration-200'
                      >
                        {link.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom Bar */}
        <div className='py-5 border-t border-gray-300/60 flex flex-col sm:flex-row items-center justify-between gap-3'>
          <p className='text-[12px] text-gray-400'>
            © {year} CortexDocs. All rights reserved.
          </p>
          <div className='flex items-center gap-6'>
            <Link
              href='#'
              className='text-[12px] text-gray-400 no-underline hover:text-gray-600 transition-colors duration-200'
            >
              Privacy Policy
            </Link>
            <Link
              href='#'
              className='text-[12px] text-gray-400 no-underline hover:text-gray-600 transition-colors duration-200'
            >
              Terms of Service
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
