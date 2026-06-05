import {api} from '../../lib/api'
import {SettingsForm} from '../../components/SettingsForm'
export default async function Page(){const rows=await api<any[]>('/api/settings'); return <div className="space-y-6"><h1 className="text-3xl font-bold">Settings</h1><p className="text-sm text-slate-400">配置 SearXNG、自动运行、Action 门槛、blocked terms。Secret 已脱敏；保存时会写入后端 SQLite。</p><SettingsForm rows={rows}/></div>}
