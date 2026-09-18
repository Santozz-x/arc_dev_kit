import Link from 'next/link'
import { cookies } from 'next/headers'
import { Header } from '@/components/Header'
import { Footer } from '@/components/Footer'
import { LogoMark } from '@/components/Logo'
import { i18n, tr, type Locale } from '@/lib/i18n'
import {
  Zap,
  Bot,
  Bug,
  BarChart2,
  Terminal,
  Layers,
  ArrowRight,
  ChevronRight,
} from 'lucide-react'

export default async function Home() {
  const store = await cookies()
  const lang = (store.get('arc-lang')?.value ?? 'pt') as Locale

  const MODULES = [
    {
      icon: Bot,
      title: 'Dev Copilot',
      desc: tr(i18n.home.copilotDesc, lang),
      href: '/docs/modules/dev-copilot',
      color: 'from-violet-500 to-arc-500',
    },
    {
      icon: Zap,
      title: 'Payment Agent',
      desc: tr(i18n.home.paymentDesc, lang),
      href: '/docs/modules/payment-agent',
      color: 'from-arc-500 to-blue-500',
    },
    {
      icon: Layers,
      title: 'Monitor Agent',
      desc: tr(i18n.home.monitorDesc, lang),
      href: '/docs/modules/monitor-agent',
      color: 'from-blue-500 to-cyan-500',
    },
    {
      icon: Bug,
      title: 'Tx Debugger',
      desc: tr(i18n.home.debuggerDesc, lang),
      href: '/docs/modules/tx-debugger',
      color: 'from-rose-500 to-orange-500',
    },
    {
      icon: BarChart2,
      title: 'Portfolio Analyzer',
      desc: tr(i18n.home.portfolioDesc, lang),
      href: '/docs/modules/portfolio-analyzer',
      color: 'from-emerald-500 to-teal-500',
    },
    {
      icon: Terminal,
      title: 'CLI & REST API',
      desc: tr(i18n.home.cliDesc, lang),
      href: '/docs/cli-reference',
      color: 'from-amber-500 to-yellow-500',
    },
  ]

  return (
    <div className="min-h-screen bg-zinc-950">
      <Header />

      {/* Hero */}
      <section className="relative pt-32 pb-20 px-6 overflow-hidden">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-arc-600/20 rounded-full blur-[120px]" />
          <div className="absolute top-20 left-1/4 w-[400px] h-[300px] bg-usdc/10 rounded-full blur-[100px]" />
        </div>

        <div className="relative max-w-4xl mx-auto text-center">
          <LogoMark size={88} className="mx-auto mb-6 shadow-xl shadow-arc-500/10 rounded-[21px]" />
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-arc-500/15 border border-arc-500/30 text-arc-300 text-xs font-medium mb-6">
            <span className="w-1.5 h-1.5 rounded-full bg-arc-400 animate-pulse" />
            {tr(i18n.home.heroBadge, lang)}
          </div>

          <h1 className="text-5xl sm:text-6xl font-bold text-white mb-6 leading-tight tracking-tight">
            {tr(i18n.home.heroTitle, lang)}{' '}
            <span className="arc-gradient-text">{tr(i18n.home.heroAccent, lang)}</span>
          </h1>

          <p className="text-lg text-zinc-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            {tr(i18n.home.heroSubtitle, lang)}
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mb-14">
            <Link
              href="/docs/getting-started"
              className="flex items-center gap-2 px-6 py-3 rounded-xl bg-arc-600 hover:bg-arc-500 text-white font-medium transition-all hover:shadow-lg hover:shadow-arc-500/30 hover:-translate-y-0.5"
            >
              {tr(i18n.home.ctaStart, lang)}
              <ArrowRight size={16} />
            </Link>
            <Link
              href="/docs/introduction"
              className="flex items-center gap-2 px-6 py-3 rounded-xl border border-zinc-700 hover:border-zinc-500 text-zinc-300 hover:text-white font-medium transition-colors"
            >
              {tr(i18n.home.ctaDocs, lang)}
            </Link>
          </div>

          {/* Quick install */}
          <div className="max-w-xl mx-auto">
            <div className="rounded-xl bg-zinc-900 border border-zinc-700/80 overflow-hidden shadow-xl shadow-black/40">
              <div className="flex items-center justify-between px-4 py-2.5 border-b border-zinc-800 bg-zinc-900/80">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-zinc-700" />
                  <div className="w-3 h-3 rounded-full bg-zinc-700" />
                  <div className="w-3 h-3 rounded-full bg-zinc-700" />
                </div>
                <span className="text-xs text-zinc-500 font-mono">terminal</span>
              </div>
              <pre className="p-5 text-sm font-mono text-left overflow-x-auto">
                <code className="text-zinc-300">
                  <span className="text-zinc-500">{tr(i18n.home.terminalInstall, lang)}</span>{'\n'}
                  <span className="text-arc-300">pip install</span>
                  <span className="text-white"> arc-devkit</span>{'\n\n'}
                  <span className="text-zinc-500">{tr(i18n.home.terminalAskComment, lang)}</span>{'\n'}
                  <span className="text-arc-300">arcdevkit ask</span>
                  <span className="text-green-300"> &quot;How do I deploy on Arc testnet?&quot;</span>{'\n\n'}
                  <span className="text-zinc-500">{tr(i18n.home.terminalDebugComment, lang)}</span>{'\n'}
                  <span className="text-arc-300">arcdevkit debug tx</span>
                  <span className="text-yellow-300"> 0xYourTxHash</span>
                </code>
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="py-8 border-y border-zinc-800/60">
        <div className="max-w-4xl mx-auto px-6 grid grid-cols-2 sm:grid-cols-4 gap-6 text-center">
          {[
            { value: '11+', label: tr(i18n.home.statModules, lang) },
            { value: '<1s', label: tr(i18n.home.statFinality, lang) },
            { value: 'USDC', label: tr(i18n.home.statGas, lang) },
            { value: 'MIT', label: tr(i18n.home.statLicense, lang) },
          ].map((stat) => (
            <div key={stat.label}>
              <div className="text-2xl font-bold arc-gradient-text">{stat.value}</div>
              <div className="text-xs text-zinc-500 mt-1">{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Modules grid */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-white mb-3">
              {tr(i18n.home.modulesTitle, lang)}
            </h2>
            <p className="text-zinc-400">{tr(i18n.home.modulesSubtitle, lang)}</p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {MODULES.map((mod) => {
              const Icon = mod.icon
              return (
                <Link
                  key={mod.title}
                  href={mod.href}
                  className="group relative p-5 rounded-xl bg-zinc-900/60 border border-zinc-800 hover:border-zinc-600 transition-all hover:-translate-y-0.5 hover:shadow-lg hover:shadow-black/30"
                >
                  <div
                    className={`w-9 h-9 rounded-lg bg-gradient-to-br ${mod.color} flex items-center justify-center mb-3 shadow-lg`}
                  >
                    <Icon size={17} className="text-white" />
                  </div>
                  <h3 className="font-semibold text-white mb-1.5 group-hover:text-arc-300 transition-colors">
                    {mod.title}
                  </h3>
                  <p className="text-sm text-zinc-400 leading-relaxed">{mod.desc}</p>
                  <ChevronRight
                    size={14}
                    className="absolute top-5 right-5 text-zinc-600 group-hover:text-arc-400 transition-colors"
                  />
                </Link>
              )
            })}
          </div>
        </div>
      </section>

      {/* Code example */}
      <section className="py-16 px-6 bg-zinc-900/30 border-y border-zinc-800/60">
        <div className="max-w-4xl mx-auto grid md:grid-cols-2 gap-10 items-center">
          <div>
            <h2 className="text-2xl font-bold text-white mb-4">
              {tr(i18n.home.codeTitle, lang)}
            </h2>
            <p className="text-zinc-400 mb-6 leading-relaxed">
              {tr(i18n.home.codeSubtitle, lang)}
            </p>
            <ul className="space-y-2 text-sm text-zinc-400">
              {i18n.home.codeFeatures.map((feat) => (
                <li key={feat.en} className="flex items-center gap-2">
                  <span className="text-arc-400">✦</span> {tr(feat, lang)}
                </li>
              ))}
            </ul>
            <Link
              href="/docs/modules/dev-copilot"
              className="inline-flex items-center gap-2 mt-6 text-arc-300 hover:text-arc-200 text-sm font-medium transition-colors"
            >
              {tr(i18n.home.codeLinkText, lang)} <ArrowRight size={14} />
            </Link>
          </div>

          <div className="rounded-xl bg-zinc-950 border border-zinc-700/80 overflow-hidden shadow-xl">
            <div className="flex items-center gap-2 px-4 py-2.5 border-b border-zinc-800 bg-zinc-900">
              <div className="w-2 h-2 rounded-full bg-arc-500" />
              <span className="text-xs text-zinc-500 font-mono">dev_copilot.py</span>
            </div>
            <pre className="p-5 text-sm font-mono overflow-x-auto">
              <code>
                <span className="text-arc-400">from</span>
                <span className="text-white"> arc_devkit.copilot.agent </span>
                <span className="text-arc-400">import</span>
                <span className="text-white"> DevCopilot</span>{'\n\n'}
                <span className="text-zinc-500"># Instantiate — context is built-in</span>{'\n'}
                <span className="text-white">copilot = </span>
                <span className="text-blue-300">DevCopilot</span>
                <span className="text-white">()</span>{'\n\n'}
                <span className="text-zinc-500"># Ask anything about Arc</span>{'\n'}
                <span className="text-white">answer = copilot.</span>
                <span className="text-blue-300">ask</span>
                <span className="text-white">(</span>{'\n'}
                <span className="text-white">    </span>
                <span className="text-green-300">&quot;How do I send USDC on Arc?&quot;</span>{'\n'}
                <span className="text-white">)</span>{'\n\n'}
                <span className="text-zinc-500"># Streaming output</span>{'\n'}
                <span className="text-arc-400">for</span>
                <span className="text-white"> chunk </span>
                <span className="text-arc-400">in</span>
                <span className="text-white"> copilot.</span>
                <span className="text-blue-300">ask_stream</span>
                <span className="text-white">(prompt):</span>{'\n'}
                <span className="text-white">    </span>
                <span className="text-arc-400">print</span>
                <span className="text-white">(chunk, end=</span>
                <span className="text-green-300">&quot;&quot;</span>
                <span className="text-white">)</span>
              </code>
            </pre>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-6">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            {tr(i18n.home.ctaTitle, lang)}
          </h2>
          <p className="text-zinc-400 mb-8">{tr(i18n.home.ctaSubtitle, lang)}</p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              href="/docs/getting-started"
              className="flex items-center gap-2 px-6 py-3 rounded-xl bg-arc-600 hover:bg-arc-500 text-white font-medium transition-all hover:shadow-lg hover:shadow-arc-500/30"
            >
              {tr(i18n.home.ctaInstall, lang)}
              <ArrowRight size={16} />
            </Link>
            <a
              href="https://github.com/Jeielsantosdev/arc_dev_kit"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-6 py-3 rounded-xl border border-zinc-700 hover:border-zinc-500 text-zinc-300 hover:text-white font-medium transition-colors"
            >
              {tr(i18n.home.ctaGithub, lang)}
            </a>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  )
}
