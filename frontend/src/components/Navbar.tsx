"use client";

import Link from "next/link";
import { Zap } from "lucide-react";

const NAV_LINKS = [
  { label: "Features", href: "#features" },
  { label: "Solutions", href: "#solutions" },
  { label: "System Design", href: "/system-design" },
];

export function Navbar() {
  return (
    <nav className='sticky top-0 z-[9999] h-16 bg-white/80 backdrop-blur-xl backdrop-saturate-[180%] border-b border-gray-200/60'>
      <div className='max-w-[1200px] w-full h-full mx-auto px-6 flex items-center justify-between'>
        {/* Logo */}
        <Link href='/' className='flex items-center gap-2.5 no-underline group'>
          <div className='w-8 h-8 rounded-lg bg-black flex items-center justify-center'>
            <Zap className='w-4 h-4 text-white' />
          </div>
          <span className='text-[15px] font-semibold text-gray-900 tracking-tight'>
            CortexDocs
          </span>
        </Link>

        {/* Center Nav */}
        <div className='hidden md:flex items-center gap-8'>
          {NAV_LINKS.map((link) => (
            <Link
              key={link.label}
              href={link.href}
              className='text-[14px] text-gray-500 font-medium no-underline hover:text-gray-900 transition-colors duration-200'
            >
              {link.label}
            </Link>
          ))}
        </div>

        {/* Right */}
        <div className='flex items-center gap-5'>
          <Link
            href='/system-design'
            className='hidden sm:inline text-[14px] text-gray-500 font-medium no-underline hover:text-gray-900 transition-colors duration-200'
          >
            Architecture
          </Link>
          <Link
            href='#dashboard'
            className='text-[13px] font-medium px-5 py-2.5 rounded-full bg-gray-900 text-white hover:bg-gray-800 transition-all duration-200 no-underline'
          >
            Get Started
          </Link>
        </div>
      </div>
    </nav>
  );
}
