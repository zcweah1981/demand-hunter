import Link from 'next/link'
import {api} from '../../../lib/api'
import {SettingsHeader} from '../../../components/SettingsHeader'

function priceLabel(price:string){
 const map:any={free:'免费',free_quota:'免费额度',free_optional:'免费可选',free_limited:'免费但受限',paid_free_trial:'付费/试用',paid_limited:'付费/强限制',paid:'付费'}
 return map[price]||price
}
function badgeClass(price:string){
 if(price==='free'||price==='free_quota'||price==='free_optional') return 'badge badge-action'
 if(String(price).includes('trial')||String(price).includes('limited')) return 'badge badge-watch'
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
    <div>
     <div className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-300">API KEY CENTER</div>
     <h1 className="mt-2 text-3xl font-black">API Key 管理中心</h1>
     <p className="mt-2 max-w-3xl text-sm text-slate-400">固定 Key 类型，统一列表管理。新增走独立页面；组合型凭证在同一个新增页面一次填完。</p>
    </div>
    <Link className="btn no-underline" href="/settings/api-keys/new">新增 Key</Link>
   </div>
   <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-slate-300">
    <div>轮询策略：<b>{data.rotation_strategy}</b></div>
    <div className="mt-1 text-xs text-slate-500">可用搜索源：{(data.available_providers||[]).join(', ')||'none'}</div>
   </div>
  </section>

  <section className="overflow-hidden rounded-3xl border border-slate-800 bg-slate-950/70 shadow-xl shadow-black/10">
   <div className="grid grid-cols-[1.5fr_0.9fr_0.8fr_0.7fr_1.4fr_90px] gap-3 border-b border-slate-800 bg-slate-900/70 px-5 py-3 text-xs font-bold uppercase tracking-wider text-slate-500">
    <div>类型</div><div>费用</div><div>已保存</div><div>状态</div><div>Key 列表</div><div className="text-right">操作</div>
   </div>
   <div className="divide-y divide-slate-800">
    {sorted.map((t:any)=>{
     const poolItems=t.pool?.items||[]
     const maskedItems=poolItems.length?poolItems:(t.items||[])
     const active=(data.available_providers||[]).includes(t.provider)
     return <div key={t.id} className="grid grid-cols-[1.5fr_0.9fr_0.8fr_0.7fr_1.4fr_90px] items-center gap-3 px-5 py-4 text-sm hover:bg-slate-900/50">
      <div>
       <div className="font-black text-slate-100">{t.title}</div>
       <div className="mt-1 text-xs text-slate-500">{t.category}</div>
       <div className="mt-1 font-mono text-[11px] text-slate-700">{t.setting_key}</div>
      </div>
      <div><span className={badgeClass(t.price)}>{priceLabel(t.price)}</span><div className="mt-1 text-xs text-slate-500">{t.free_quota||'—'}</div></div>
      <div className="text-slate-200"><b>{t.count||0}</b> 条</div>
      <div>{active?<span className="badge badge-action">可用</span>:(t.count>0?<span className="badge badge-watch">未接入</span>:<span className="badge">未配置</span>)}</div>
      <div className="space-y-1">
       {maskedItems.length?maskedItems.slice(0,5).map((it:any)=><div key={it.index} className="flex items-center justify-between gap-2 rounded-xl border border-slate-800 bg-slate-900/60 px-2 py-1 font-mono text-xs text-slate-400"><span>{it.masked}</span>{it.stats&&<span className="font-sans text-[11px] text-slate-500">ok {it.stats?.ok||0} / fail {it.stats?.fail||0}</span>}</div>):<span className="text-xs text-slate-600">暂无 Key</span>}
       {maskedItems.length>5&&<div className="text-xs text-slate-600">还有 {maskedItems.length-5} 条...</div>}
      </div>
      <div className="text-right"><Link className="btn-secondary no-underline" href={`/settings/api-keys/new?type=${t.id}`}>新增</Link></div>
     </div>
    })}
   </div>
  </section>
 </div>
}
