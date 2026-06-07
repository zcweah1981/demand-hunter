import {api} from '../../../lib/api'
import {SettingsForm} from '../../../components/SettingsForm'
import {SettingsHeader} from '../../../components/SettingsHeader'

export default async function Page({params}:{params:Promise<{group:string}>}){
 const rows=await api<any[]>('/api/settings')
 const {group='search'}=await params
 return <div className="space-y-6"><SettingsHeader group={group}/><SettingsForm rows={rows} initialGroup={group}/></div>
}
