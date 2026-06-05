import './globals.css'
import {Nav} from '../components/Nav'
import {AuthGate} from '../components/AuthGate'
export const metadata={title:'Demand Hunter Web'}
export default function Layout({children}:{children:React.ReactNode}){return <html lang="en"><body><AuthGate><div className="flex"><Nav/><main className="flex-1 p-8">{children}</main></div></AuthGate></body></html>}
