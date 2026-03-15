import Link from "next/link"

export function LandingFooter() {
  return (
    <footer className="border-t border-[#DDDDDD] bg-white">
      <div className="max-w-6xl mx-auto px-6 py-10 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-[#767676] flex items-center justify-center">
            <span className="text-[#FF5A5F] font-bold text-sm leading-none">L</span>
          </div>
          <div>
            <span className="font-semibold text-[#484848] text-sm">LEPA</span>
            <p className="text-xs text-[#767676] leading-none mt-0.5">Account Intelligence for B2B Sales</p>
          </div>
        </div>

        <div className="flex items-center gap-6 text-xs text-[#767676]">
          <Link href="/sign-in" className="hover:text-[#484848] transition-colors">Sign in</Link>
          <Link href="#how-it-works" className="hover:text-[#484848] transition-colors">How it works</Link>
          <Link href="#features" className="hover:text-[#484848] transition-colors">Features</Link>
        </div>

        <p className="text-xs text-[#767676]">
          &copy; {new Date().getFullYear()} LEPA. All rights reserved.
        </p>
      </div>
    </footer>
  )
}
