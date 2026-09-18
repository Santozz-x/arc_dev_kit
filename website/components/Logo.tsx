import Link from 'next/link'
import Image from 'next/image'

export function LogoMark({ size = 36, className = '' }: { size?: number; className?: string }) {
  return (
    <Image src="/brand/arc-devkit-mark.svg" alt="" width={size} height={size} className={`shrink-0 ${className}`} />
  )
}

export function Logo({ className }: { className?: string }) {
  return (
    <Link href="/" aria-label="Arc DevKit — Home" className={`flex shrink-0 items-center gap-2.5 group rounded-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-arc-300 ${className ?? ''}`}>
      <LogoMark />
      <div className="flex flex-col gap-1 leading-none">
        <span className="text-white font-semibold text-sm tracking-tight">Arc <span className="text-arc-200">DevKit</span></span>
        <span className="text-zinc-400 text-[9px] font-mono tracking-[0.16em] uppercase">Python Toolkit</span>
      </div>
    </Link>
  )
}
