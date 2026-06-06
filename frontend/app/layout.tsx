import './globals.css'
import {Nav} from '../components/Nav'
import {AuthGate} from '../components/AuthGate'

export const metadata = {title: 'Demand Hunter Web'}

export default function Layout({children}: {children: React.ReactNode}) {
  return (
    <html lang="en">
      <body>
        <AuthGate>
          <div className="min-h-screen lg:flex">
            <Nav />
            <main className="min-w-0 flex-1 p-4 sm:p-6 lg:p-8">{children}</main>
          </div>
        </AuthGate>
      </body>
    </html>
  )
}
