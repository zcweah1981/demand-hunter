'use client'

import {useState, useTransition} from 'react'
import {useRouter} from 'next/navigation'
import {api} from '../lib/api'

export function DiscoveryPruneButton(){
  const router = useRouter()
  const [msg,setMsg] = useState('')
  const [err,setErr] = useState('')
  const [pending,startTransition] = useTransition()
  return <div className="flex flex-col items-start gap-2">
    <button className="btn-secondary" disabled={pending} onClick={()=>{
      setMsg(''); setErr('')
      startTransition(async()=>{
        try{
          const r = await api<any>('/api/discovery/prune',{method:'POST'})
          setMsg(`Pruned expansions=${r.pruned_expansions}, competitor keywords=${r.pruned_competitor_keywords}, keywords=${r.updated_keywords}`)
          router.refresh()
        }catch(e:any){ setErr(e.message || 'Prune failed') }
      })
    }}>{pending?'Pruning...':'Prune low-quality discoveries'}</button>
    {msg&&<span className="text-xs text-emerald-300">{msg}</span>}
    {err&&<span className="text-xs text-rose-300">{err}</span>}
  </div>
}
