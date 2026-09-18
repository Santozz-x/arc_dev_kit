'use client'

import Link from 'next/link'
import { Menu, X, Github, ExternalLink } from 'lucide-react'
import { Logo } from './Logo'
import { useLanguage } from './LanguageProvider'
import { i18n, tr } from '@/lib/i18n'

interface HeaderProps {
  onMenuToggle?: () => void
  menuOpen?: boolean
}

export function Header({ onMenuToggle, menuOpen }: HeaderProps) {
  const { lang, setLang } = useLanguage()

  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-14 border-b border-zinc-800/80 bg-zinc-950/90 backdrop-blur-md">
      <div className="flex h-full items-center gap-4 px-4">
        <button
          onClick={onMenuToggle}
          className="lg:hidden p-1.5 rounded-md text-zinc-400 hover:text-white hover:bg-white/5 transition-colors"
          aria-label="Toggle menu"
        >
          {menuOpen ? <X size={18} /> : <Menu size={18} />}
        </button>

        <Logo />

        <nav className="hidden md:flex items-center gap-1 ml-4">
          <NavLink href="/docs/introduction">{tr(i18n.nav.docs, lang)}</NavLink>
          <NavLink href="/docs/getting-started">{tr(i18n.nav.quickstart, lang)}</NavLink>
          <NavLink href="/docs/rest-api">{tr(i18n.nav.api, lang)}</NavLink>
          <NavLink href="/docs/cookbook">{tr(i18n.nav.cookbook, lang)}</NavLink>
          <NavLink href="/demo">{tr(i18n.nav.demo, lang)}</NavLink>
        </nav>

        <div className="ml-auto flex items-center gap-2">
          {/* Language toggle */}
          <div className="flex items-center gap-0.5 rounded-md border border-zinc-700/60 overflow-hidden text-xs font-medium">
            <button
              onClick={() => setLang('pt')}
              className={
                lang === 'pt'
                  ? 'px-2 py-1 bg-arc-600 text-white'
                  : 'px-2 py-1 text-zinc-500 hover:text-white hover:bg-white/5 transition-colors'
              }
            >
              PT
            </button>
            <span className="text-zinc-700">|</span>
            <button
              onClick={() => setLang('en')}
              className={
                lang === 'en'
                  ? 'px-2 py-1 bg-arc-600 text-white'
                  : 'px-2 py-1 text-zinc-500 hover:text-white hover:bg-white/5 transition-colors'
              }
            >
              EN
            </button>
          </div>

          <span className="hidden sm:inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-arc-500/20 border border-arc-500/30 text-arc-300 text-xs font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-arc-400 animate-pulse" />
            v0.10.0
          </span>

          <a
            href="https://github.com/Jeielsantosdev/arc_dev_kit"
            target="_blank"
            rel="noopener noreferrer"
            className="p-1.5 rounded-md text-zinc-400 hover:text-white hover:bg-white/5 transition-colors"
            aria-label="GitHub"
          >
            <Github size={18} />
          </a>

          <a
            href="https://pypi.org/project/arc-devkit/"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-arc-600 hover:bg-arc-500 text-white transition-colors"
          >
            pip install
            <ExternalLink size={11} />
          </a>
        </div>
      </div>
    </header>
  )
}

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="px-3 py-1.5 rounded-md text-sm text-zinc-400 hover:text-white hover:bg-white/5 transition-colors"
    >
      {children}
    </Link>
  )
}
