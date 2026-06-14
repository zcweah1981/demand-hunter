'use client'

import {usePathname} from 'next/navigation'
import {AuthGate} from './AuthGate'
import {AutomationStatusBar} from './AutomationStatusBar'
import {Nav} from './Nav'

export function AppShell({children}: {children: React.ReactNode}) {
  const pathname = usePathname()
  const isLogin = pathname?.startsWith('/login')

  if (isLogin) {
    return <>{children}</>
  }

  return (
    <AuthGate>
      <div className="min-h-screen md:flex">
        <Nav />
        <main className="min-w-0 flex-1 p-4 sm:p-6 md:p-8">
          <AutomationStatusBar />
          {children}
        </main>
      </div>
    </AuthGate>
  )
}
