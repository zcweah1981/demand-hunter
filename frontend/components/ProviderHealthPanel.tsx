'use client'
import {useState} from 'react'
import {api} from '../lib/api'
import {useLang} from '../lib/i18n'

function okBadge(ok:boolean){return <span className={ok?'badge badge-action':'badge badge-reject'}>{ok?'OK':'FAIL'}</span>}
export function ProviderHealthPanel(){
 const {lang,t}=useLang()
 const [health,setHealth]=useState<any>(null)
 const [loading,setLoading]=useState(false)
 const [err,setErr]=useState('')
 async function run(){setLoading(true); setErr(''); try{setHealth(await api('/api/settings/provider-health',{method:'POST'}))}catch(e:any){setErr(e.message||'failed')} finally{setLoading(false)}}
 return <div className="space-y-4">
  <button className="btn-secondary" disabled={loading} onClick={run}>{loading?t('testing'):t('providerHealth')}</button>
  {err&&<div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-200">{err}</div>}
  {health&&<div className="grid gap-4 lg:grid-cols-3">
    <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
      <div className="mb-3 flex items-center justify-between"><h3 className="font-bold">SearXNG</h3><span className="badge">{health.searxng?.length||0} URLs</span></div>
      <div className="space-y-2">{(health.searxng||[]).map((x:any)=><div key={x.url} className="rounded-xl bg-slate-900 p-3 text-xs"><div className="mb-1 flex items-center justify-between gap-2"><code className="truncate">{x.url}</code>{okBadge(!!x.ok)}</div><div className="text-slate-500">{x.elapsed_ms}ms · {x.results||0} results</div>{x.error&&<div className="mt-1 text-rose-300">{x.error}</div>}</div>)}</div>
    </div>
    {['brave','tavily'].map((p)=><div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4" key={p}>
      <div className="mb-3 flex items-center justify-between"><h3 className="font-bold capitalize">{p}</h3>{okBadge(!!health[p]?.ok)}</div>
      <div className="grid gap-2 text-sm text-slate-300">
        <div className="flex justify-between"><span>{lang==='en'?'Configured':'已配置'}</span><b>{String(!!health[p]?.configured)}</b></div>
        <div className="flex justify-between"><span>{lang==='en'?'Keys':'Key 数量'}</span><b>{health[p]?.keys||0}</b></div>
        <div className="flex justify-between"><span>{lang==='en'?'Results':'结果'}</span><b>{health[p]?.results||0}</b></div>
      </div>
    </div>)}
    <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4 lg:col-span-3"><div className="text-xs uppercase tracking-wide text-slate-500">Available providers</div><div className="mt-2 flex flex-wrap gap-2">{(health.available||[]).map((p:string)=><span className="badge badge-action" key={p}>{p}</span>)}</div></div>
  </div>}
 </div>
}
