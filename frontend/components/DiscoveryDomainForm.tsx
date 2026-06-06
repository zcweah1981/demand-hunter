'use client'

import {useState, useTransition} from 'react'
import {useRouter} from 'next/navigation'
import {api} from '../lib/api'

export function DiscoveryDomainForm(){
  const router = useRouter()
  const [domain,setDomain] = useState('')
  const [results,setResults] = useState<any>(null)
  const [error,setError] = useState('')
  const [pending,startTransition] = useTransition()

  async function submit(e:React.FormEvent){
    e.preventDefault()
    if(!domain.trim()) return
    setError(''); setResults(null)
    startTransition(async()=>{
      try{
        const clean = domain.replace(/^https?:\/\//,'').replace(/^www\./,'').split('/')[0]
        const [keywords,sites] = await Promise.all([
          api<any[]>('/api/discovery/site-keywords',{method:'POST',body:JSON.stringify({domain:clean})}),
          api<any[]>('/api/discovery/similar-sites',{method:'POST',body:JSON.stringify({domain:clean})}),
        ])
        setResults({keywords,sites})
        router.refresh()
      }catch(err:any){ setError(err.message || 'Discovery failed') }
    })
  }

  return <form onSubmit={submit} className="mt-5 space-y-4">
    <div className="flex flex-col gap-3 sm:flex-row">
      <input className="input flex-1" value={domain} onChange={e=>setDomain(e.target.value)} placeholder="example.com" />
      <button className="btn" disabled={pending || !domain.trim()}>{pending?'Running...':'Run domain discovery'}</button>
    </div>
    {error&&<p className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-200">{error}</p>}
    {results&&<div className="grid gap-3 text-sm md:grid-cols-2">
      <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4"><b className="text-cyan-300">Keywords</b><div className="mt-1 text-slate-400">{results.keywords.length} keywords found</div></div>
      <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4"><b className="text-emerald-300">Similar Sites</b><div className="mt-1 text-slate-400">{results.sites.length} sites found</div></div>
    </div>}
  </form>
}
