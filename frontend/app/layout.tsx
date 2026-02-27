import type { Metadata } from 'next'
import Link from 'next/link'
import './globals.css'

export const metadata: Metadata = {
  title: 'xAID Signal Radar',
  description: 'B2B lead signal monitoring for radiology AI sales',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col">
        {/* Top navigation */}
        <nav className="bg-white border-b border-gray-200 sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-14">
              {/* Brand */}
              <div className="flex items-center gap-6">
                <Link href="/" className="flex items-center gap-2 text-blue-700 font-bold text-lg tracking-tight hover:text-blue-800 transition-colors">
                  <RadarIcon className="w-5 h-5" />
                  <span>Signal Radar</span>
                </Link>

                {/* Nav links */}
                <div className="hidden sm:flex items-center gap-1">
                  <NavLink href="/">Dashboard</NavLink>
                  <NavLink href="/companies">Companies</NavLink>
                  <NavLink href="/adjacent">Adjacent Leads</NavLink>
                </div>
              </div>

              {/* Right side */}
              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-400 hidden sm:block">xAID Sales Intelligence</span>
              </div>
            </div>
          </div>
        </nav>

        {/* Page content */}
        <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6">
          {children}
        </main>

        {/* Footer */}
        <footer className="border-t border-gray-100 py-4">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <p className="text-xs text-gray-400 text-center">xAID Signal Radar — internal sales tool</p>
          </div>
        </footer>
      </body>
    </html>
  )
}

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="px-3 py-1.5 rounded-md text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition-colors"
    >
      {children}
    </Link>
  )
}

function RadarIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0" />
      <path d="M12 12m-5 0a5 5 0 1 0 10 0a5 5 0 1 0 -10 0" />
      <path d="M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0" />
      <path d="M15 9l3.35 -3.35" />
    </svg>
  )
}
