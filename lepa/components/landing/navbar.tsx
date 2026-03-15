import Link from "next/link"

export function LandingNavbar() {
  return (
    <header className="fixed top-0 inset-x-0 z-50 bg-[#F7F7F7]/90 backdrop-blur-sm border-b border-[#DDDDDD]">
      <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-[#767676] flex items-center justify-center">
            <span className="text-[#FF5A5F] font-bold text-sm leading-none">L</span>
          </div>
          <span className="font-semibold text-[#484848] tracking-tight text-base">LEPA</span>
        </Link>

        <nav className="hidden md:flex items-center gap-7 text-sm text-[#767676]">
          <Link href="#how-it-works" className="hover:text-[#484848] transition-colors">How it works</Link>
          <Link href="#features" className="hover:text-[#484848] transition-colors">Features</Link>
        </nav>

        <div className="flex items-center gap-3">
          <Link href="/sign-in" className="text-sm text-[#767676] hover:text-[#484848] transition-colors">
            Sign in
          </Link>
          <Link href="/sign-up" className="text-sm bg-[#FF5A5F] text-white px-4 py-1.5 rounded font-medium hover:opacity-90 transition-opacity">
            Try free
          </Link>
        </div>
      </div>
    </header>
  )
}
