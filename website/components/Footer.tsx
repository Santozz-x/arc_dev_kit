'use client'

import Link from 'next/link'
import { Github } from 'lucide-react'
import { useLanguage } from './LanguageProvider'
import { i18n, tr } from '@/lib/i18n'

export function Footer() {
  const { lang } = useLanguage()

  return (
    <footer className="border-t border-zinc-800/80 bg-zinc-950 py-8 mt-16">
      <div className="max-w-5xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-sm text-zinc-500">
          <span className="w-5 h-5 rounded bg-gradient-to-br from-arc-400 to-arc-600 inline-block" />
          <span>Arc DevKit</span>
          <span className="text-zinc-700">·</span>
          <span>{tr(i18n.footer.license, lang)}</span>
          <span className="text-zinc-700">·</span>
          <span>v0.10.0</span>
        </div>

        <div className="flex items-center gap-4 text-sm text-zinc-500">
          <Link href="/docs/introduction" className="hover:text-white transition-colors">
            {tr(i18n.footer.docs, lang)}
          </Link>
          <Link href="/docs/cookbook" className="hover:text-white transition-colors">
            {tr(i18n.footer.cookbook, lang)}
          </Link>
          <a
            href="https://github.com/Jeielsantosdev/arc_dev_kit"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-white transition-colors flex items-center gap-1"
          >
            <Github size={14} />
            GitHub
          </a>
        </div>
      </div>
    </footer>
  )
}
