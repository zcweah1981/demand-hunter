'use client'
import {useState} from 'react'
import Link from 'next/link'
import {ApiKeyActions} from './ApiKeyActions'

function priceLabel(price:string){
 const map:any={free:'免费',free_quota:'免费额度',free_optional:'免费可选',free_limited:'免费但受限',paid_free_trial:'付费/试用',paid_limited:'付费/强限制',paid:'付费'}
 return map[price]||price
}
function badgeClass(price:string){
 if(price==='free'||price==='free_quota'||price==='free_optional') return 'badge badge-action'
 if(String(price).includes('trial')||String(price).includes('limited')) return 'badge badge-watch'
 return 'badge badge-reject'
}

export function ApiKeyCenter({data,types}:{data:any;types:any[]}){
 const [selected,setSelected]=useState<any|null>(null)
 const available=data.available_providers||[]
 return <>
  <section className="overflow-hidden rounded-3xl border border-slate-800 bg-slate-950/70 shadow-xl shadow-black/10">
   <div className="grid grid-cols-[1.5fr_0.9fr_0.8fr_0.7fr_1.4fr_90px] gap-3 border-b border-slate-800 bg-slate-900/70 px-5 py-3 text-xs font-bold uppercase tracking-wider text-slate-500">
    <div>类型</div><div>费用</div><div>已保存</div><div>状态</div><div>Key 预览</div><div className="text-right">管理</div>
   </div>
   <div className="divide-y divide-slate-800">
    {types.map((t:any)=>{
     const poolItems=t.pool?.items||[]
     const maskedItems=poolItems.length?poolItems:(t.items||[])
     const active=available.includes(t.provider)
     return <button key={t.id} className="grid w-full grid-cols-[1.5fr_0.9fr_0.8fr_0.7fr_1.4fr_90px] items-center gap-3 px-5 py-4 text-left text-sm hover:bg-slate-900/50" onClick={()=>setSelected({...t,maskedItems,active})}>
      <div>
       <div className="font-black text-slate-100">{t.title}</div>
       <div className="mt-1 text-xs text-slate-500">{t.category}</div>
       <div className="mt-1 font-mono text-[11px] text-slate-700">{t.setting_key}</div>
      </div>
      <div><span className={badgeClass(t.price)}>{priceLabel(t.price)}</span><div className="mt-1 text-xs text-slate-500">{t.free_quota||'—'}</div></div>
      <div className="text-slate-200"><b>{t.count||0}</b> 条</div>
      <div>{active?<span className="badge badge-action">可用</span>:(t.count>0?<span className="badge badge-watch">未接入</span>:<span className="badge">未配置</span>)}</div>
      <div className="space-y-1">
       {maskedItems.length?maskedItems.slice(0,3).map((it:any)=><div key={it.index} className="flex items-center justify-between gap-2 rounded-xl border border-slate-800 bg-slate-900/60 px-2 py-1 font-mono text-xs text-slate-400"><span>{it.masked}</span>{it.stats&&<span className="font-sans text-[11px] text-slate-500">ok {it.stats?.ok||0} / fail {it.stats?.fail||0}</span>}</div>):<span className="text-xs text-slate-600">暂无 Key</span>}
       {maskedItems.length>3&&<div className="text-xs text-slate-600">还有 {maskedItems.length-3} 条...</div>}
      </div>
      <div className="text-right"><span className="btn-secondary no-underline">管理</span></div>
     </button>
    })}
   </div>
  </section>

  {selected&&<div className="fixed inset-0 z-50">
   <button className="absolute inset-0 bg-black/60" aria-label="关闭" onClick={()=>setSelected(null)} />
   <aside className="absolute right-0 top-0 h-full w-full max-w-2xl overflow-y-auto border-l border-slate-800 bg-slate-950 p-6 shadow-2xl">
    <div className="flex items-start justify-between gap-3">
     <div>
      <div className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-300">API KEY DRAWER</div>
      <h2 className="mt-2 text-2xl font-black text-white">{selected.title}</h2>
      <p className="mt-1 text-sm text-slate-400">{selected.category} · {selected.free_quota||'—'}</p>
      <p className="mt-1 font-mono text-xs text-slate-600">{selected.setting_key}</p>
     </div>
     <button className="btn-secondary" onClick={()=>setSelected(null)}>关闭</button>
    </div>

    <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
     <div><div className="text-sm text-slate-300">已保存 <b className="text-white">{selected.count||0}</b> 条</div><div className="mt-1 text-xs text-slate-500">在这里修改或删除该类型下的 Key。</div></div>
     <Link className="btn no-underline" href={`/settings/api-keys/new?type=${selected.id}`}>新增 Key</Link>
    </div>

    <div className="mt-5 space-y-3">
     {selected.maskedItems?.length?selected.maskedItems.map((it:any)=><div key={it.index} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
       <div>
        <div className="text-xs font-semibold text-slate-500">#{it.index}</div>
        <div className="mt-1 font-mono text-sm text-slate-200">{it.masked}</div>
        {it.stats&&<div className="mt-1 text-xs text-slate-500">ok {it.stats?.ok||0} / fail {it.stats?.fail||0}</div>}
       </div>
       <ApiKeyActions typeId={selected.id} index={it.index}/>
      </div>
     </div>):<div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 text-sm text-slate-500">暂无 Key。点击右上角“新增 Key”添加。</div>}
    </div>
   </aside>
  </div>}
 </>
}
