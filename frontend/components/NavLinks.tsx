'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

const NAV_ITEMS = [
  { href: '/',          label: 'Dashboard' },
  { href: '/companies', label: 'Companies' },
  { href: '/adjacent',  label: 'Adjacent Leads' },
]

export default function NavLinks() {
  const pathname = usePathname()

  return (
    <div className="hidden sm:flex items-center gap-1">
      {NAV_ITEMS.map(({ href, label }) => {
        const isActive = href === '/' ? pathname === '/' : pathname.startsWith(href)
        return (
          <Link
            key={href}
            href={href}
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              isActive
                ? 'bg-blue-50 text-blue-700 font-semibold'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            }`}
          >
            {label}
          </Link>
        )
      })}
    </div>
  )
}
