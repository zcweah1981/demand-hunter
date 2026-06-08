import Link from 'next/link'
import {api} from '../../../lib/api'
import {SettingsHeader} from '../../../components/SettingsHeader'
import {ApiKeyCenter} from '../../../components/ApiKeyCenter'

export default async function Page(){
 const data=await api<any>('/api/settings/api-key-types')
 const types=data.types||[]
 const primary=['serpapi','zenserp','scaleserp','brave','tavily']
 const sorted=[...types].sort((a,b)=>{
  const ai=primary.indexOf(a.id), bi=primary.indexOf(b.id)
  if(ai!==-1||bi!==-1) return (ai===-1?999:ai)-(bi===-1?999:bi)
  return String(a.title).localeCompare(String(b.title))
 })
 return <div className="space-y-6">
  <SettingsHeader group="api-keys"/>
  <section className="rounded-3xl border border-blue-500/20 bg-gradient-to-br from-slate-950 to-blue-950/40 p-6 shadow-2xl">
   <div className="flex flex-wrap items-center justify-between gap-3">
    <div>
     <div className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-300">API KEY CENTER</div>
     <h1 className="mt-2 text-3xl font-black">API Key 管理中心</h1>
     <p className="mt-2 max-w-3xl text-sm text-slate-400">点击任意 Key 类型打开右侧抽屉，在抽屉里新增、修改或删除该类型的 Key。</p>
    </div>
    <Link className="btn no-underline" href="/settings/api-keys/new">新增 Key</Link>
   </div>
   <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-slate-300">
    <div>轮询策略：<b>{data.rotation_strategy}</b></div>
    <div className="mt-1 text-xs text-slate-500">可用搜索源：{(data.available_providers||[]).join(', ')||'none'}</div>
   </div>
  </section>
  <ApiKeyCenter data={data} types={sorted}/>
 </div>
}
