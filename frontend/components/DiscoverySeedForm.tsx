'use client'

import {useState, useTransition} from 'react'
import {useRouter} from 'next/navigation'
import {api} from '../lib/api'
import {pollJob} from '../lib/jobPoll'

export function DiscoverySeedForm(){
  const router = useRouter()
  const [seed,setSeed] = useState('')
  const [results,setResults] = useState<any>(null)
  const [error,setError] = useState('')
  const [pending,startTransition] = useTransition()

  async function submit(e:React.FormEvent){
    e.preventDefault()
    if(!seed.trim()) return
    setError(''); setResults(null)
    startTransition(async()=>{
      try{
        const [expansions,sites] = await Promise.all([
          pollJob(api, '/api/discovery/expand', {seed}, {maxWait:90000}),
          pollJob(api, '/api/discovery/find-sites', {seed}, {maxWait:90000}),
        ])
        setResults({expansions,sites})
        router.refresh()
      }catch(err:any){ setError(err.message || 'Discovery failed') }
    })
  }

  return <form onSubmit={submit} className="mt-5 space-y-4">
    <div className="flex flex-col gap-3 sm:flex-row">
      <input className="input flex-1" value={seed} onChange={e=>setSeed(e.target.value)} placeholder="invoice late fee calculator" />
      <button className="btn" disabled={pending || !seed.trim()}>{pending?'Running API...':'Run keyword discovery'}</button>
    </div>
    {error&&<p className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-200">{error}</p>}
    {results&&<div className="grid gap-3 text-sm md:grid-cols-2">
      <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4"><b className="text-violet-300">Expanded</b><div className="mt-1 text-slate-400">{results.expansions.length} keywords found</div></div>
      <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4"><b className="text-blue-300">Sites</b><div className="mt-1 text-slate-400">{results.sites.length} SERP domains found</div></div>
    </div>}
  </form>
}
