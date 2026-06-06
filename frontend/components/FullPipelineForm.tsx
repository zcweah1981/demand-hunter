'use client'

import {useState, useTransition} from 'react'
import {useRouter} from 'next/navigation'
import {api} from '../lib/api'
import {pollJob} from '../lib/jobPoll'

export function FullPipelineForm(){
  const router = useRouter()
  const [seed,setSeed] = useState('')
  const [depth,setDepth] = useState(2)
  const [summary,setSummary] = useState<any>(null)
  const [error,setError] = useState('')
  const [pending,startTransition] = useTransition()

  async function submit(e:React.FormEvent){
    e.preventDefault()
    if(!seed.trim()) return
    setError(''); setSummary(null)
    startTransition(async()=>{
      try{
        const data = await pollJob<any>(api, '/api/discovery/run-and-import', {seed,depth,import_limit:12}, {maxWait:180000, interval:3000})
        setSummary(data)
        router.refresh()
      }catch(err:any){ setError(err.message || 'Pipeline failed') }
    })
  }

  return <form onSubmit={submit} className="mt-5 space-y-4">
    <div className="grid gap-3 md:grid-cols-[1fr_120px_auto]">
      <input className="input" value={seed} onChange={e=>setSeed(e.target.value)} placeholder="chargeback evidence template" />
      <input className="input" type="number" min={1} max={5} value={depth} onChange={e=>setDepth(Number(e.target.value)||2)} />
      <button className="btn" disabled={pending || !seed.trim()}>{pending?'Running API pipeline...':'Run + import via API'}</button>
    </div>
    {error&&<p className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-200">{error}</p>}
    {summary&&<div className="grid gap-3 text-sm md:grid-cols-5">
      <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4"><b>Expanded</b><div className="mt-1 text-slate-400">{summary.expanded_keywords?.length||0}</div></div>
      <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4"><b>Sites</b><div className="mt-1 text-slate-400">{summary.sites?.length||0}</div></div>
      <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4"><b>Competitor KWs</b><div className="mt-1 text-slate-400">{summary.competitor_keywords?.length||0}</div></div>
      <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4"><b>Similar Sites</b><div className="mt-1 text-slate-400">{summary.similar_sites?.length||0}</div></div>
      <div className="rounded-2xl border border-emerald-500/30 bg-emerald-950/20 p-4"><b>Imported</b><div className="mt-1 text-emerald-300">{summary.imported_keywords?.length||0}</div></div>
    </div>}
  </form>
}
