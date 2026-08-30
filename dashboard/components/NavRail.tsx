'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function NavRail() {
  const pathname = usePathname();

  const navItems = [
    {
      name: 'Overview',
      href: '/',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <rect x="3" y="3" width="7" height="7" strokeWidth="1.5" />
          <rect x="14" y="3" width="7" height="7" strokeWidth="1.5" />
          <rect x="3" y="14" width="7" height="7" strokeWidth="1.5" />
          <rect x="14" y="14" width="7" height="7" strokeWidth="1.5" />
        </svg>
      ),
    },
    {
      name: 'Exceptions',
      href: '/exceptions',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="square" strokeLinejoin="miter" strokeWidth="1.5" d="M12 9v3.75m0 3.75h.008v.008H12v-.008zM12 3L2 21h20L12 3z" />
        </svg>
      ),
    },
    {
      name: 'Ask AI',
      href: '/ask',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="square" strokeLinejoin="miter" strokeWidth="1.5" d="M8.25 3v1.5M12 3v1.5M15.75 3v1.5M3 8.25h18M3 12h18M3 15.75h18M3 19.5h18" />
        </svg>
      ),
    },
  ];

  return (
    <aside className="w-full md:w-[64px] md:min-w-[64px] h-14 md:h-auto bg-[#010306] text-[#ffffff] border-b md:border-b-0 md:border-r border-[#c6c6cb] flex md:flex-col items-center justify-between md:justify-start px-4 md:px-0 py-2 md:py-4 space-y-0 md:space-y-6 select-none z-10">
      {/* Brand Icon Block */}
      <div className="w-9 h-9 md:w-10 md:h-10 border border-[#44474d] flex items-center justify-center font-serif text-sm font-medium tracking-tight text-[#ffffff] bg-[#1a1d23]">
        ML
      </div>

      {/* Navigation Items */}
      <nav className="flex md:flex-col space-x-3 md:space-x-0 md:space-y-4 items-center">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              title={item.name}
              className={`w-9 h-9 md:w-11 md:h-11 flex items-center justify-center transition-colors focus-visible:outline-2 focus-visible:outline-[#ffffff] ${
                isActive
                  ? 'bg-[#fcf9f2] text-[#010306] font-semibold'
                  : 'text-[#ffffff] hover:bg-[#1a1d23] rounded'
              }`}
            >
              {item.icon}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
