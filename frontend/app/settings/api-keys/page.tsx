import Link from 'next/link'
import {api} from '../../../lib/api'
import {SettingsHeader} from '../../../components/SettingsHeader'

function priceLabel(price:string){
 const map:any={free:'免费',free_quota:'免费额度',free_optional:'免费可选',free_limited:'免费但受限',paid_free_trial:'付费/试用',paid_limited:'付费/强限制',paid:'付费'}
 return map[price]||price
}
function badgeClass(price:string){
 if(price==='free'||price==='free_quota'||price==='free_optional') return 'badge badge-action'
 if(price.includes('trial')||price.includes('limited')) return 'badge badge-watch'
 return 'badge badge-reject'
}

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
    <div><div className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-300">API KEY CENTER</div><h1 className="mt-2 text-3xl font-black">API Key 管理中心</h1><p className="mt-2 max-w-3xl text-sm text-slate-400">所有采集器和搜索源的 Key 都固定类型、列表管理。新增 Key 进入独立页面；Brave、Tavily、SerpApi、Zenserp、Scale SERP 都在这里统一轮询。</p></div>
    <div className="rounded-2xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-slate-300"><div>轮询策略：<b>{data.rotation_strategy}</b></div><div className="mt-1 text-xs text-slate-500">可用搜索源：{(data.available_providers||[]).join(', ')||'none'}</div></div>
   </div>
  </section>
  <section className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
   {sorted.map((t:any)=><div key={t.id} className="rounded-3xl border border-slate-800 bg-slate-950/70 p-5 shadow-xl shadow-black/10">
    <div className="mb-4 flex items-start justify-between gap-3"><div><h3 className="text-lg font-black text-slate-100">{t.title}</h3><p className="mt-1 text-xs text-slate-500">{t.category}</p></div><span className={badgeClass(t.price)}>{priceLabel(t.price)}</span></div>
    <div className="space-y-2 text-sm text-slate-300"><div>已保存：<b>{t.count||0}</b> 条</div><div className="text-xs text-slate-500">免费/额度：{t.free_quota||'—'}</div><div className="font-mono text-xs text-slate-600">{t.setting_key}</div></div>
    {t.pool?.items?.length>0&&<div className="mt-3 rounded-2xl border border-slate-800 bg-slate-900/60 p-3"><div className="mb-2 text-xs font-bold text-slate-400">轮询状态</div><div className="space-y-1">{t.pool.items.slice(0,4).map((it:any)=><div key={it.index} className="flex justify-between gap-2 text-xs text-slate-400"><code>{it.masked}</code><span>ok {it.stats?.ok||0} / fail {it.stats?.fail||0}</span></div>)}</div></div>}
    <div className="mt-4 flex gap-2"><Link className="btn flex-1 text-center no-underline" href={`/settings/api-keys/new?type=${t.id}`}>新增</Link></div>
   </div>)}
  </section>
 </div>
}
