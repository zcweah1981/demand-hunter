import {NextRequest, NextResponse} from 'next/server'

export function middleware(req: NextRequest){
  const {pathname} = req.nextUrl
  if(pathname.startsWith('/login') || pathname.startsWith('/_next') || pathname === '/favicon.ico') return NextResponse.next()
  const required = process.env.INTERNAL_API_TOKEN || ''
  if(!required) return NextResponse.next()
  const cookie = req.cookies.get('dh_token')?.value || ''
  if(cookie !== required){
    const url = req.nextUrl.clone(); url.pathname = '/login'; url.search = ''
    return NextResponse.redirect(url)
  }
  return NextResponse.next()
}

export const config = { matcher: ['/((?!api).*)'] }
