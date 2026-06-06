import {api} from '../../../lib/api'
import {SettingsForm} from '../../../components/SettingsForm'
const names:any={search:'Search Providers',brave:'Brave',tavily:'Tavily',llm:'LLM',automation:'Automation',quality:'Quality',security:'Security'}
export default async function Page({params}:{params:{group:string}}){
 const rows=await api<any[]>('/api/settings')
 const group=params.group||'search'
 return <div className="space-y-6"><div><h1 className="text-3xl font-bold">Settings / {names[group]||group}</h1><p className="mt-2 text-slate-400">分组配置中心：搜索源、模型、自动任务、质量门槛和安全设置。</p></div><SettingsForm rows={rows} initialGroup={group}/></div>
}
