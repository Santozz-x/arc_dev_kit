'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { getNav } from '@/lib/nav'
import { slugToHref } from '@/lib/utils'
import { cn } from '@/lib/utils'
import { useLanguage } from './LanguageProvider'
import { i18n, tr } from '@/lib/i18n'

interface SidebarProps {
  open?: boolean
  onClose?: () => void
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const pathname = usePathname()
  const { lang } = useLanguage()
  const nav = getNav(lang)

  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={cn(
          'fixed top-14 left-0 bottom-0 z-40 w-[280px] bg-zinc-950 border-r border-zinc-800/80',
          'overflow-y-auto overscroll-contain',
          'transition-transform duration-200 ease-in-out',
          'lg:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <nav className="px-3 py-4 pb-16">
          {nav.map((group) => (
            <div key={group.section}>
              <p className="sidebar-section">{group.section}</p>
              <ul className="space-y-0.5">
                {group.items.map((item) => {
                  const href = slugToHref(item.slug)
                  const isActive = pathname === href
                  return (
                    <li key={href}>
                      <Link
                        href={href}
                        onClick={onClose}
                        className={cn('sidebar-link', isActive && 'active')}
                      >
                        {item.title}
                      </Link>
                    </li>
                  )
                })}
              </ul>
            </div>
          ))}

          <div className="mt-8 mx-3 p-3 rounded-lg bg-arc-500/10 border border-arc-500/20">
            <p className="text-xs font-medium text-arc-300 mb-1">
              {tr(i18n.sidebar.network, lang)}
            </p>
            <p className="text-xs text-zinc-500">Chain ID: 5042</p>
            <p className="text-xs text-zinc-500 mt-0.5 break-all">rpc.mainnet.arc.io</p>
            <p className="text-xs text-zinc-600 mt-1.5 break-all">
              Testnet: 5042002 · rpc.testnet.arc.io
            </p>
          </div>
        </nav>
      </aside>
    </>
  )
}
