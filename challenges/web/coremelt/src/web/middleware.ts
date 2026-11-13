import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// ── ICARUS access control ─────────────────────────────────────────────────
// The CoreWatch dashboard itself is public (flavour). The privileged areas —
// the engineering / admin / RTU-control consoles — are "gated": any GET to them
// is rewritten to the not-found view, so they answer as if a middleware auth
// layer is hiding them. This is the DECOY (RazorHack "Coremelt"): it mimics a
// Next.js middleware auth gate (CVE-2025-29927) and baits players into the
// x-middleware-subrequest / hidden-route rabbit hole. There is NO real console
// behind it. The actual bug is the RSC deserializer (CVE-2025-55182), reached by
// the server-action POST path on `/`, which is left open.
const GATED = /^\/(admin|engineering|controls|rtu|console|internal)(\/|$)/i

export function middleware(req: NextRequest) {
  if (req.method === 'GET' && GATED.test(req.nextUrl.pathname)) {
    return NextResponse.rewrite(new URL('/_not-found', req.url))
  }
  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
