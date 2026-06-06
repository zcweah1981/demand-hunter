import {api} from '../../lib/api'
import {SettingsForm} from '../../components/SettingsForm'
export default async function Page(){const rows=await api<any[]>('/api/settings'); return <div className="space-y-6"><div><h1 className="text-3xl font-bold">Settings</h1><p className="mt-2 text-slate-400">上线配置中心。先确保 Search Test 通过，再调整自动运行和质量门槛。</p></div><SettingsForm rows={rows}/></div>}
