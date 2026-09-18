'use client'

import { useCallback, useEffect, useState } from 'react'
import { Header } from '@/components/Header'
import { Footer } from '@/components/Footer'
import { useLanguage } from '@/components/LanguageProvider'
import { i18n, tr } from '@/lib/i18n'
import {
  CheckCircle2,
  XCircle,
  Loader2,
  RefreshCw,
  Search,
  Shuffle,
  ExternalLink,
  AlertTriangle,
  Radio,
} from 'lucide-react'

// Public, build-time env var — the only way this page knows where the
// read-only demo backend lives. Never guessed, never a user-supplied value:
// there is no input anywhere on this page for a visitor to pick their own
// RPC or API URL.
const API_BASE = (process.env.NEXT_PUBLIC_DEMO_API_URL || '').replace(/\/$/, '')

// Recorded once, live, against real Arc Mainnet — see docs/mainnet/MAINNET_DEMO.md
// for the full session. This is a frozen snapshot, not a live query: it's
// shown so the page still demonstrates something concrete even when
// NEXT_PUBLIC_DEMO_API_URL isn't configured for this deployment.
const HISTORICAL_TX = {
  hash: '0xafcc72e47de265ed4dc2f584f8e1a325a4cf45d24f41e299da76becdb76dcc74',
  status: 'success',
  block: 21530719,
  from: '0x6F6F3613577bB5c8234067C5a6E299ff26C2Eb63',
  to: '0x80Aa550313c04d4987b06185E37cc7C03cA9f233',
  value_native_usdc: '524.671261',
  gas_used: 156309,
  gas_cost_native_usdc: '0.003241033754439057',
  explorer_url:
    'https://explorer.arc.io/tx/0xafcc72e47de265ed4dc2f584f8e1a325a4cf45d24f41e299da76becdb76dcc74',
  usdc_erc20_transfers_decoded: [
    {
      from: '0x80aa550313c04d4987b06185e37cc7c03ca9f233',
      to: '0x78f84f129196494f0b34671e14bd5e57278a162d',
      amount_usdc: '524.671261',
    },
  ],
  recorded_at_utc: '2026-09-18T17:07:48Z',
}

type FetchState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ok'; data: T }

interface StatusData {
  queried_at_utc: string
  network: string
  explorer_url: string
  rpc_url: string
  ready: boolean
  rpc_ok: boolean
  rpc_error: string | null
  latency_ms: number | null
  expected_chain_id: number | null
  rpc_chain_id: number | null
  chain_id_match: boolean
  usdc_contract_ok: boolean
  explorer_configured: boolean
}

interface BlockData {
  queried_at_utc: string
  number: number
  hash: string
  timestamp_utc: string
  tx_count: number
}

interface TxData {
  queried_at_utc: string
  hash: string
  status: string
  block: number
  from: string
  to: string
  value_native_usdc: string
  gas_used: number
  gas_cost_native_usdc: string
  explorer_url: string
  usdc_erc20_transfers_decoded: { from: string; to: string; amount_usdc: string }[]
  debug_analysis: {
    network: string
    status: string
    custo_usdc: string
    revert_reason: string | null
    summary: string
  }
}

async function fetchJson<T>(path: string): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, { cache: 'no-store' })
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(body.detail || `HTTP ${resp.status}`)
  }
  return resp.json()
}

export default function DemoPage() {
  const { lang } = useLanguage()
  const d = i18n.demo
  const configured = API_BASE.length > 0

  const [status, setStatus] = useState<FetchState<StatusData>>({ status: 'idle' })
  const [block, setBlock] = useState<FetchState<BlockData>>({ status: 'idle' })
  const [tx, setTx] = useState<FetchState<TxData>>({ status: 'idle' })
  const [txInput, setTxInput] = useState('')

  const loadStatus = useCallback(() => {
    if (!configured) return
    setStatus({ status: 'loading' })
    fetchJson<StatusData>('/demo/status')
      .then((data) => setStatus({ status: 'ok', data }))
      .catch((err) => setStatus({ status: 'error', message: String(err.message || err) }))
  }, [configured])

  const loadBlock = useCallback(() => {
    if (!configured) return
    setBlock({ status: 'loading' })
    fetchJson<BlockData>('/demo/block/latest')
      .then((data) => setBlock({ status: 'ok', data }))
      .catch((err) => setBlock({ status: 'error', message: String(err.message || err) }))
  }, [configured])

  const lookupTx = useCallback(
    (hash: string) => {
      if (!configured || !hash) return
      if (!/^0x[0-9a-fA-F]{64}$/.test(hash)) {
        setTx({ status: 'error', message: tr(d.invalidHash, lang) })
        return
      }
      setTx({ status: 'loading' })
      fetchJson<TxData>(`/demo/tx/${hash}`)
        .then((data) => setTx({ status: 'ok', data }))
        .catch((err) => setTx({ status: 'error', message: String(err.message || err) }))
    },
    [configured, d.invalidHash, lang]
  )

  const findRecentTx = useCallback(() => {
    if (!configured) return
    setTx({ status: 'loading' })
    fetchJson<{ tx_hash: string }>('/demo/tx/find?scan_blocks=30')
      .then((found) => {
        setTxInput(found.tx_hash)
        return fetchJson<TxData>(`/demo/tx/${found.tx_hash}`)
      })
      .then((data) => setTx({ status: 'ok', data }))
      .catch((err) => setTx({ status: 'error', message: String(err.message || err) }))
  }, [configured])

  useEffect(() => {
    loadStatus()
    loadBlock()
  }, [loadStatus, loadBlock])

  return (
    <div className="min-h-screen bg-zinc-950">
      <Header />

      <section className="pt-28 pb-16 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center gap-3 mb-3">
            <h1 className="text-3xl sm:text-4xl font-bold text-white">{tr(d.title, lang)}</h1>
            {configured ? (
              <Badge tone="live" icon={<Radio size={12} />}>
                {tr(d.liveBadge, lang)}
              </Badge>
            ) : (
              <Badge tone="warn" icon={<AlertTriangle size={12} />}>
                {tr(d.unavailableBadge, lang)}
              </Badge>
            )}
          </div>
          <p className="text-zinc-400 max-w-2xl leading-relaxed mb-10">{tr(d.subtitle, lang)}</p>

          {!configured && (
            <div className="mb-10 rounded-xl border border-amber-500/30 bg-amber-500/10 p-5">
              <div className="flex items-center gap-2 text-amber-300 font-medium mb-1.5">
                <AlertTriangle size={16} />
                {tr(d.notConfiguredTitle, lang)}
              </div>
              <p className="text-sm text-amber-200/80 leading-relaxed">
                {tr(d.notConfiguredBody, lang)}
              </p>
            </div>
          )}

          {/* Status card */}
          <Card title={tr(d.statusTitle, lang)}>
            {!configured ? (
              <UnavailableRow />
            ) : status.status === 'loading' || status.status === 'idle' ? (
              <LoadingRow />
            ) : status.status === 'error' ? (
              <ErrorRow message={status.message} />
            ) : (
              <>
                <div className="grid sm:grid-cols-2 gap-x-8 gap-y-2 text-sm">
                  <Field label={tr(d.network, lang)} value={status.data.network} />
                  <Field
                    label={tr(d.chainIdMatch, lang)}
                    value={
                      status.data.chain_id_match ? (
                        <span className="text-emerald-400 flex items-center gap-1">
                          <CheckCircle2 size={14} /> {status.data.rpc_chain_id}
                        </span>
                      ) : (
                        <span className="text-rose-400 flex items-center gap-1">
                          <XCircle size={14} /> {status.data.rpc_chain_id} ≠{' '}
                          {status.data.expected_chain_id}
                        </span>
                      )
                    }
                  />
                  <Field label={tr(d.chainIdExpected, lang)} value={status.data.expected_chain_id} />
                  <Field
                    label={tr(d.latency, lang)}
                    value={status.data.latency_ms ? `${status.data.latency_ms} ms` : '—'}
                  />
                  <Field
                    label={tr(d.usdcContract, lang)}
                    value={status.data.usdc_contract_ok ? '✓' : '✗'}
                  />
                  <Field label={tr(d.queriedAt, lang)} value={status.data.queried_at_utc} mono />
                </div>
                <RefreshButton onClick={loadStatus} label={tr(d.refresh, lang)} />
              </>
            )}
          </Card>

          {/* Latest block card */}
          <Card title={tr(d.blockTitle, lang)}>
            {!configured ? (
              <UnavailableRow />
            ) : block.status === 'loading' || block.status === 'idle' ? (
              <LoadingRow />
            ) : block.status === 'error' ? (
              <ErrorRow message={block.message} />
            ) : (
              <>
                <div className="grid sm:grid-cols-2 gap-x-8 gap-y-2 text-sm">
                  <Field label={tr(d.blockNumber, lang)} value={`#${block.data.number.toLocaleString()}`} />
                  <Field label={tr(d.blockTxCount, lang)} value={block.data.tx_count} />
                  <Field label={tr(d.blockHash, lang)} value={block.data.hash} mono truncate />
                  <Field label={tr(d.blockTimestamp, lang)} value={block.data.timestamp_utc} mono />
                </div>
                <RefreshButton onClick={loadBlock} label={tr(d.refresh, lang)} />
              </>
            )}
          </Card>

          {/* Transaction lookup card */}
          <Card title={tr(d.txTitle, lang)}>
            <div className="flex flex-col sm:flex-row gap-2 mb-4">
              <input
                type="text"
                value={txInput}
                onChange={(e) => setTxInput(e.target.value)}
                placeholder={tr(d.txInputPlaceholder, lang)}
                disabled={!configured}
                className="flex-1 px-3 py-2 rounded-lg bg-zinc-900 border border-zinc-700 text-sm text-zinc-200 font-mono placeholder:text-zinc-600 focus:outline-none focus:border-arc-500 disabled:opacity-50"
              />
              <button
                onClick={() => lookupTx(txInput.trim())}
                disabled={!configured}
                className="flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg bg-arc-600 hover:bg-arc-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors whitespace-nowrap"
              >
                <Search size={14} />
                {tr(d.txLookupButton, lang)}
              </button>
              <button
                onClick={findRecentTx}
                disabled={!configured}
                className="flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg border border-zinc-700 hover:border-zinc-500 disabled:opacity-40 disabled:cursor-not-allowed text-zinc-300 text-sm font-medium transition-colors whitespace-nowrap"
              >
                <Shuffle size={14} />
                {tr(d.txFindButton, lang)}
              </button>
            </div>

            {!configured ? (
              <UnavailableRow />
            ) : tx.status === 'idle' ? (
              <p className="text-sm text-zinc-500">↑</p>
            ) : tx.status === 'loading' ? (
              <LoadingRow />
            ) : tx.status === 'error' ? (
              <ErrorRow message={tx.message} />
            ) : (
              <TxResult data={tx.data} lang={lang} d={d} />
            )}
          </Card>

          {/* Recorded session video */}
          <Card title={tr(d.recordingTitle, lang)} muted>
            <p className="text-sm text-zinc-500 mb-4">{tr(d.recordingBody, lang)}</p>
            {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
            <video
              controls
              preload="metadata"
              playsInline
              className="w-full rounded-lg border border-zinc-800 bg-black"
            >
              <source src="/recording/arc_devkit_mainnet_demo.webm" type="video/webm" />
              <source src="/recording/arc_devkit_mainnet_demo.mp4" type="video/mp4" />
              {tr(d.recordingFallback, lang)}
            </video>
            <div className="mt-3 flex flex-wrap gap-4 text-xs">
              <a
                href="/recording/arc_devkit_mainnet_demo.mp4"
                download
                className="text-zinc-500 hover:text-zinc-300 underline underline-offset-2"
              >
                {tr(d.recordingDownloadMp4, lang)}
              </a>
              <a
                href="/recording/arc_devkit_mainnet_demo.cast"
                download
                className="text-zinc-500 hover:text-zinc-300 underline underline-offset-2"
              >
                {tr(d.recordingDownloadCast, lang)}
              </a>
            </div>
          </Card>

          {/* Historical reference */}
          <Card title={tr(d.historicalTitle, lang)} muted>
            <p className="text-sm text-zinc-500 mb-4">{tr(d.historicalBody, lang)}</p>
            <TxResult
              data={{
                queried_at_utc: HISTORICAL_TX.recorded_at_utc,
                hash: HISTORICAL_TX.hash,
                status: HISTORICAL_TX.status,
                block: HISTORICAL_TX.block,
                from: HISTORICAL_TX.from,
                to: HISTORICAL_TX.to,
                value_native_usdc: HISTORICAL_TX.value_native_usdc,
                gas_used: HISTORICAL_TX.gas_used,
                gas_cost_native_usdc: HISTORICAL_TX.gas_cost_native_usdc,
                explorer_url: HISTORICAL_TX.explorer_url,
                usdc_erc20_transfers_decoded: HISTORICAL_TX.usdc_erc20_transfers_decoded,
                debug_analysis: {
                  network: 'Arc Mainnet',
                  status: HISTORICAL_TX.status,
                  custo_usdc: HISTORICAL_TX.gas_cost_native_usdc,
                  revert_reason: null,
                  summary: `Status: success | Gas used: ${HISTORICAL_TX.gas_used} | Cost: ${HISTORICAL_TX.gas_cost_native_usdc} USDC`,
                },
              }}
              lang={lang}
              d={d}
              historical
            />
            <a
              href="https://github.com/Jeielsantosdev/arc-devkit/blob/main/docs/mainnet/MAINNET_DEMO.md"
              target="_blank"
              rel="noopener noreferrer"
              className="mt-4 inline-block text-sm text-emerald-600 dark:text-emerald-400 hover:underline"
            >
              {tr(d.historicalLink, lang)}
            </a>
          </Card>

          {/* Python code + install */}
          <Card title={tr(d.codeTitle, lang)}>
            <CodeBlock
              code={`from arc_devkit import Arc

arc = Arc.mainnet()

health = arc.health_check()
block = arc.latest_block()
tx = arc.get_transaction(tx_hash)
report = arc.debug_transaction(tx_hash, use_ai=False)`}
            />
          </Card>

          <Card title={tr(d.installTitle, lang)}>
            <CodeBlock code={'pip install arc-devkit'} />
          </Card>
        </div>
      </section>

      <Footer />
    </div>
  )
}

function TxResult({
  data,
  lang,
  d,
  historical,
}: {
  data: TxData
  lang: 'pt' | 'en'
  d: typeof i18n.demo
  historical?: boolean
}) {
  return (
    <div className={historical ? 'opacity-90' : ''}>
      <div className="grid sm:grid-cols-2 gap-x-8 gap-y-2 text-sm mb-4">
        <Field label={tr(d.txHash, lang)} value={data.hash} mono truncate full />
        <Field
          label={tr(d.txStatus, lang)}
          value={
            data.status === 'success' ? (
              <span className="text-emerald-400 flex items-center gap-1">
                <CheckCircle2 size={14} /> {data.status}
              </span>
            ) : (
              <span className="text-rose-400 flex items-center gap-1">
                <XCircle size={14} /> {data.status}
              </span>
            )
          }
        />
        <Field label={tr(d.txBlock, lang)} value={`#${data.block?.toLocaleString?.() ?? data.block}`} />
        <Field label={tr(d.txFrom, lang)} value={data.from} mono truncate />
        <Field label={tr(d.txTo, lang)} value={data.to} mono truncate />
        <Field label={tr(d.txValueNative, lang)} value={`${data.value_native_usdc} USDC`} />
        <Field label={tr(d.txGasCost, lang)} value={`${data.gas_cost_native_usdc} USDC`} />
        <Field label={tr(d.queriedAt, lang)} value={data.queried_at_utc} mono />
      </div>

      <div className="mb-4">
        <div className="text-xs font-medium text-zinc-500 mb-1.5">
          {tr(d.txErc20Transfers, lang)}
        </div>
        {data.usdc_erc20_transfers_decoded.length === 0 ? (
          <p className="text-sm text-zinc-600">{tr(d.txNoErc20, lang)}</p>
        ) : (
          <div className="space-y-1">
            {data.usdc_erc20_transfers_decoded.map((t, i) => (
              <div key={i} className="text-xs font-mono text-zinc-400 bg-zinc-900/60 rounded px-2 py-1.5">
                {t.from} → {t.to}: <span className="text-usdc">{t.amount_usdc} USDC</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="mb-4 rounded-lg bg-zinc-900/60 border border-zinc-800 p-3">
        <div className="text-xs font-medium text-zinc-500 mb-1">{tr(d.debugTitle, lang)}</div>
        <p className="text-sm text-zinc-300">{data.debug_analysis.summary}</p>
      </div>

      <a
        href={data.explorer_url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1.5 text-sm text-arc-300 hover:text-arc-200 transition-colors"
      >
        {tr(d.viewExplorer, lang)} <ExternalLink size={13} />
      </a>
    </div>
  )
}

function Card({
  title,
  children,
  muted,
}: {
  title: string
  children: React.ReactNode
  muted?: boolean
}) {
  return (
    <div
      className={`mb-6 rounded-xl border p-5 ${
        muted ? 'border-zinc-800/60 bg-zinc-900/30' : 'border-zinc-800 bg-zinc-900/60'
      }`}
    >
      <h2 className="text-sm font-semibold text-white mb-4">{title}</h2>
      {children}
    </div>
  )
}

function Field({
  label,
  value,
  mono,
  truncate,
  full,
}: {
  label: string
  value: React.ReactNode
  mono?: boolean
  truncate?: boolean
  full?: boolean
}) {
  return (
    <div className={full ? 'sm:col-span-2' : ''}>
      <div className="text-xs text-zinc-500">{label}</div>
      <div
        className={`text-zinc-200 ${mono ? 'font-mono text-xs' : 'text-sm'} ${
          truncate ? 'truncate' : 'break-all'
        }`}
      >
        {value}
      </div>
    </div>
  )
}

function Badge({
  tone,
  icon,
  children,
}: {
  tone: 'live' | 'warn'
  icon: React.ReactNode
  children: React.ReactNode
}) {
  const cls =
    tone === 'live'
      ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300'
      : 'bg-amber-500/15 border-amber-500/30 text-amber-300'
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium ${cls}`}
    >
      {icon}
      {children}
    </span>
  )
}

function LoadingRow() {
  return (
    <div className="flex items-center gap-2 text-sm text-zinc-500 py-2">
      <Loader2 size={14} className="animate-spin" />
      …
    </div>
  )
}

function ErrorRow({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 text-sm text-rose-400 py-2">
      <XCircle size={14} className="mt-0.5 shrink-0" />
      <span className="break-all">{message}</span>
    </div>
  )
}

function UnavailableRow() {
  const { lang } = useLanguage()
  return (
    <div className="flex items-start gap-2 text-sm text-amber-400/90 py-2">
      <AlertTriangle size={14} className="mt-0.5 shrink-0" />
      <span>{tr(i18n.demo.unavailableBody, lang)}</span>
    </div>
  )
}

function RefreshButton({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      className="mt-4 inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white transition-colors"
    >
      <RefreshCw size={12} />
      {label}
    </button>
  )
}

function CodeBlock({ code }: { code: string }) {
  return (
    <pre className="p-4 rounded-lg bg-zinc-950 border border-zinc-800 text-xs font-mono text-zinc-300 overflow-x-auto">
      <code>{code}</code>
    </pre>
  )
}
