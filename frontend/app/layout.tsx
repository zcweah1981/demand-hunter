import './globals.css'
import {AppShell} from '../components/AppShell'

export const metadata = {title: 'Demand Hunter Web'}

export default function Layout({children}: {children: React.ReactNode}) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  )
}
